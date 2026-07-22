##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.float_utils import float_compare, float_is_zero


@tagged("post_install", "-at_install")
class TestCancelRemainingMultistep(TransactionCase):
    """Matriz completa de button_cancel_remaining en ventas.

    Ejes cubiertos:
      * pasos de entrega: 1 (ship_only), 2 (pick_ship), 3 (pick_pack_ship)
      * generación de la cadena:
          - "progresivo" (push, ruta default del almacén): al confirmar solo se
            crea el 1er picking; los siguientes por push al completar el anterior.
            ``sale_line_id`` va en cada move.
          - "juntos" (pull/MTO): la cadena entera se crea al confirmar; ``sale_line_id``
            queda SOLO en el OUT.
      * estado de entrega al cancelar: nada / 1er paso full / 1er paso parcial /
        multinivel (PICK+PACK done) / split (parte entregada + parte en tránsito).

    Invariantes tras cancelar remanente:
      1. la línea baja a ``qty_delivered + quantity_returned``;
      2. no queda demanda "forward" huérfana (ningún move vivo empujando hacia el cliente);
      3. lo ya movido a una ubicación intermedia (tránsito) se puede devolver a Stock
         (hay retorno pendiente que, validado, deja CERO stock varado);
      4. lo ya entregado al cliente no se toca.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        cls.customer_loc = cls.env.ref("stock.stock_location_customers")
        cls.partner = cls.env["res.partner"].create({"name": "Cliente Cancel Remaining"})
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")

        cls.wh1 = cls._make_wh("ship_only", "TC1")
        cls.wh2 = cls._make_wh("pick_ship", "TC2")
        cls.wh3 = cls._make_wh("pick_pack_ship", "TC3")
        cls.mto2 = cls._make_mto_route(cls.wh2, 2)
        cls.mto3 = cls._make_mto_route(cls.wh3, 3)

        # usuario de ventas SIN el permiso 'Picking cancelation allow' (stock_ux),
        # para el escenario del ticket 122867 (el que cancela no es admin de stock).
        groups = cls.env.ref("base.group_user") | cls.env.ref("sales_team.group_sale_salesman")
        stock_user = cls.env.ref("stock.group_stock_user", raise_if_not_found=False)
        if stock_user:
            groups |= stock_user
        cls.restricted_user = cls.env["res.users"].create(
            {
                "name": "Vendedor Restringido",
                "login": "vendedor_restringido_test",
                "email": "vendedor@test.com",
                "groups_id": [(6, 0, groups.ids)],
            }
        )
        cls.company.email = cls.company.email or "company@test.com"
        cls.partner.email = cls.partner.email or "cliente@test.com"
        # En el bundle completo, sale_exception puede bloquear confirmar/entregar.
        if cls.env["sale.order"]._fields.get("ignore_exception"):
            cls.env["exception.rule"].search([("active", "=", True)]).write({"active": False})

    # ---------------- infra ----------------
    @classmethod
    def _make_wh(cls, steps, code):
        wh = cls.env["stock.warehouse"].search([("code", "=", code)], limit=1)
        if not wh:
            wh = cls.env["stock.warehouse"].create(
                {"name": "Bench %s" % code, "code": code, "company_id": cls.company.id, "delivery_steps": steps}
            )
        if wh.delivery_steps != steps:
            wh.delivery_steps = steps
        return wh

    @classmethod
    def _make_mto_route(cls, wh, n):
        name = "MTO %s %sp" % (wh.code, n)
        route = cls.env["stock.route"].search([("name", "=", name)], limit=1)
        if route:
            return route
        if n == 3:
            legs = [
                ("pick", wh.lot_stock_id, wh.wh_pack_stock_loc_id, wh.pick_type_id, "make_to_stock"),
                ("pack", wh.wh_pack_stock_loc_id, wh.wh_output_stock_loc_id, wh.pack_type_id, "make_to_order"),
                ("out", wh.wh_output_stock_loc_id, cls.customer_loc, wh.out_type_id, "make_to_order"),
            ]
        else:
            legs = [
                ("pick", wh.lot_stock_id, wh.wh_output_stock_loc_id, wh.pick_type_id, "make_to_stock"),
                ("out", wh.wh_output_stock_loc_id, cls.customer_loc, wh.out_type_id, "make_to_order"),
            ]
        route = cls.env["stock.route"].create({"name": name, "product_selectable": True})
        for nm, src, dst, ptype, pm in legs:
            cls.env["stock.rule"].create(
                {
                    "name": "%s %s" % (name, nm),
                    "route_id": route.id,
                    "action": "pull",
                    "procure_method": pm,
                    "location_src_id": src.id,
                    "location_dest_id": dst.id,
                    "location_dest_from_rule": True,
                    "picking_type_id": ptype.id,
                    "warehouse_id": wh.id,
                    "company_id": cls.company.id,
                }
            )
        return route

    def _product(self, code, uom=None):
        uom = uom or self.uom_unit
        return self.env["product.product"].create(
            {
                "name": "P %s" % code,
                "default_code": code,
                "type": "consu",
                "is_storable": True,
                "invoice_policy": "order",
                "uom_id": uom.id,
                "uom_po_id": uom.id,
            }
        )

    def _stock(self, product, location, qty=1000.0):
        self.env["stock.quant"]._update_available_quantity(product, location, qty)

    def _confirm(self, product, wh, qty=10.0, route=None):
        if route:
            product.route_ids = [(6, 0, route.ids)]
        self._stock(product, wh.lot_stock_id)
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": wh.id,
                "order_line": [(0, 0, {"product_id": product.id, "product_uom_qty": qty})],
            }
        )
        so.action_confirm()
        return so

    def _next_picking(self, so):
        return so.picking_ids.filtered(lambda p: p.state not in ("done", "cancel")).sorted("id")[:1]

    def _deliver(self, picking, qty=None):
        # Mismo patrón que test_return_of_return (probado en el bundle completo de
        # runbot): confirmar, reservar, y CLAVE: borrar las move.line reservadas antes
        # de fijar la cantidad hecha. Con reserva automática al confirmar, esas líneas
        # traen cantidad 0/parcial y ``move.quantity = X`` no las pisa, así que
        # ``_action_done`` completaría 0 (qty_delivered=0).
        picking = picking.filtered(lambda p: p.state not in ("done", "cancel"))
        picking.action_confirm()
        to_assign = picking.filtered(lambda p: p.state not in ("assigned", "done", "cancel"))
        if to_assign:
            to_assign.action_assign()
        for move in picking.move_ids.filtered(lambda m: m.state not in ("done", "cancel")):
            move.move_line_ids.unlink()
            move.quantity = move.product_uom_qty if qty is None else qty
            move.picked = True
        picking._action_done()

    def _rank(self, wh, loc):
        if loc == wh.lot_stock_id:
            return 0
        if loc == wh.wh_pack_stock_loc_id:
            return 1
        if loc == wh.wh_output_stock_loc_id:
            return 2
        if loc.usage == "customer":
            return 3
        return 0 if loc.usage == "internal" else 3

    def _stranded(self, so):
        wh = so.warehouse_id
        net = {}
        for m in so.picking_ids.mapped("move_ids").filtered(lambda mv: mv.state == "done"):
            # normalizar a la UoM base del producto (los moves pueden mezclar UoM)
            qty = m.product_uom._compute_quantity(m.quantity, m.product_id.uom_id, rounding_method="HALF-UP")
            net[m.location_dest_id.id] = net.get(m.location_dest_id.id, 0.0) + qty
            net[m.location_id.id] = net.get(m.location_id.id, 0.0) - qty
        out = {}
        for loc_id, qty in net.items():
            loc = self.env["stock.location"].browse(loc_id)
            if loc.usage == "internal" and loc != wh.lot_stock_id and abs(qty) > 0.001:
                out[loc.display_name] = round(qty, 2)
        return out

    def _assert_clean_cancel(self, so, expected_delivered, msg=""):
        wh = so.warehouse_id
        line = so.order_line[:1] if len(so.order_line) > 1 else so.order_line
        line = line[0]
        # 1. la línea bajó a lo entregado
        self.assertTrue(
            float_is_zero(line.product_uom_qty - (line.qty_delivered + line.quantity_returned), precision_digits=2),
            "%s: la línea no bajó a qty_delivered+returned (uom_qty=%s delivered=%s returned=%s)"
            % (msg, line.product_uom_qty, line.qty_delivered, line.quantity_returned),
        )
        # 4. lo entregado no se tocó
        self.assertEqual(
            float_compare(line.qty_delivered, expected_delivered, precision_digits=2),
            0,
            "%s: qty_delivered=%s esperado=%s" % (msg, line.qty_delivered, expected_delivered),
        )
        # 2. no hay forward huérfano
        alive = so.picking_ids.mapped("move_ids").filtered(lambda m: m.state not in ("done", "cancel"))
        forward = alive.filtered(lambda m: self._rank(wh, m.location_dest_id) >= self._rank(wh, m.location_id))
        self.assertFalse(
            forward,
            "%s: quedó demanda forward huérfana: %s"
            % (msg, [(m.id, m.state, m.location_id.display_name, m.location_dest_id.display_name) for m in forward]),
        )
        # 3. validando los retornos pendientes queda CERO varado
        for _i in range(5):
            returns = so.picking_ids.filtered(
                lambda p: p.state not in ("done", "cancel") and p.location_dest_id == wh.lot_stock_id
            )
            if not returns:
                break
            for ret in returns:
                self._deliver(ret)
        self.assertFalse(
            self._stranded(so), "%s: quedó stock varado tras validar retornos: %s" % (msg, self._stranded(so))
        )

    # ---------------- Escenario A: cancelar sin entregar ----------------
    def test_A_sin_entrega(self):
        for n, wh, route in [
            (1, self.wh1, None),
            (2, self.wh2, None),
            (2, self.wh2, self.mto2),
            (3, self.wh3, None),
            (3, self.wh3, self.mto3),
        ]:
            mode = "juntos" if route else "progresivo"
            so = self._confirm(self._product("A%s%s" % (n, mode)), wh, route=route)
            so.order_line.button_cancel_remaining()
            self._assert_clean_cancel(so, 0.0, "A %sp %s sin entrega" % (n, mode))

    # ---------------- Escenario B: 1er paso entregado full ----------------
    def test_B_primer_paso_full(self):
        for n, wh, route in [
            (1, self.wh1, None),
            (2, self.wh2, None),
            (2, self.wh2, self.mto2),
            (3, self.wh3, None),
            (3, self.wh3, self.mto3),
        ]:
            mode = "juntos" if route else "progresivo"
            so = self._confirm(self._product("B%s%s" % (n, mode)), wh, route=route)
            self._deliver(self._next_picking(so))
            so.order_line.button_cancel_remaining()
            # en 1 paso el 1er picking ES la entrega al cliente => delivered=10
            expected = 10.0 if n == 1 else 0.0
            self._assert_clean_cancel(so, expected, "B %sp %s 1er paso full" % (n, mode))

    # ---------------- Escenario C: 1er paso parcial (4 de 10) ----------------
    def test_C_primer_paso_parcial(self):
        for n, wh, route in [
            (1, self.wh1, None),
            (2, self.wh2, None),
            (2, self.wh2, self.mto2),
            (3, self.wh3, None),
            (3, self.wh3, self.mto3),
        ]:
            mode = "juntos" if route else "progresivo"
            so = self._confirm(self._product("C%s%s" % (n, mode)), wh, route=route)
            self._deliver(self._next_picking(so), qty=4.0)
            so.order_line.button_cancel_remaining()
            expected = 4.0 if n == 1 else 0.0
            self._assert_clean_cancel(so, expected, "C %sp %s 1er paso parcial" % (n, mode))

    # ---------------- Escenario D: caso 193 - PICK+PACK ambos done ----------------
    def test_D_multinivel_pick_pack_done(self):
        so = self._confirm(self._product("D"), self.wh3, route=self.mto3)
        self._deliver(self._next_picking(so))  # PICK -> Packing
        self._deliver(self._next_picking(so))  # PACK -> Output
        # stock físico en Output, OUT pendiente
        so.order_line.button_cancel_remaining()
        self._assert_clean_cancel(so, 0.0, "D caso193 PICK+PACK done (stock en Output)")

    # ---------------- Escenario E: split entregado + tránsito multinivel ----------------
    def test_E_split_entregado_y_transito(self):
        so = self._confirm(self._product("E"), self.wh3, route=self.mto3)
        self._deliver(self._next_picking(so))  # PICK 10 -> Packing
        self._deliver(self._next_picking(so), qty=6.0)  # PACK 6 -> Output (4 quedan en Packing)
        out = so.picking_ids.filtered(
            lambda p: p.picking_type_id.code == "outgoing" and p.state not in ("done", "cancel")
        ).sorted("id")[:1]
        self._deliver(out, qty=6.0)  # OUT 6 -> cliente
        so.order_line.button_cancel_remaining()
        # 6 entregados intactos; 4 en Packing se devuelven a Stock
        self._assert_clean_cancel(so, 6.0, "E split 6 entregado / 4 en tránsito")

    # ---------------- Escenario F: 121400 reserva desde sub-ubicación ----------------
    def test_F_sub_ubicacion_sin_fantasma(self):
        product = self._product("F")
        child = self.env["stock.location"].create(
            {"name": "BINF", "location_id": self.wh1.lot_stock_id.id, "usage": "internal"}
        )
        self.env["stock.quant"]._update_available_quantity(product, child, 10.0)
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.wh1.id,
                "order_line": [(0, 0, {"product_id": product.id, "product_uom_qty": 10.0})],
            }
        )
        so.action_confirm()
        so.picking_ids.move_ids._action_assign()  # reserva desde BINF (único con stock)
        so.order_line.button_cancel_remaining()
        alive = so.picking_ids.mapped("move_ids").filtered(lambda m: m.state not in ("done", "cancel"))
        self.assertFalse(
            alive,
            "F: no debe quedar move vivo / contraentrega fantasma: %s"
            % [(m.id, m.state, m.location_id.display_name, m.location_dest_id.display_name) for m in alive],
        )

    # ---------------- Escenario G: idempotencia ----------------
    def test_G_idempotencia(self):
        so = self._confirm(self._product("G"), self.wh2, route=self.mto2)
        self._deliver(self._next_picking(so))
        so.order_line.button_cancel_remaining()
        moves_1 = len(so.picking_ids.mapped("move_ids"))
        so.order_line.button_cancel_remaining()  # 2da vez no debe romper ni duplicar retornos
        moves_2 = len(so.picking_ids.mapped("move_ids"))
        self.assertEqual(moves_1, moves_2, "G: la 2da cancelación no debe generar moves nuevos")
        self._assert_clean_cancel(so, 0.0, "G idempotencia")

    # ---------------- Escenario H: multi-línea mismo producto (moves fusionados) ----------------
    def test_H_multilinea_no_afecta_otras(self):
        """En MTO, los PICK/PACK de líneas del mismo producto se FUSIONAN (sin
        sale_line_id, cantidad sumada). Cancelar una línea debe REDUCIR esos moves
        compartidos, no cancelarlos: la otra línea tiene que seguir entregable full."""
        product = self._product("H")
        product.route_ids = [(6, 0, self.mto3.ids)]
        self._stock(product, self.wh3.lot_stock_id)
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.wh3.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": 10.0}),
                    (0, 0, {"product_id": product.id, "product_uom_qty": 10.0}),
                ],
            }
        )
        so.action_confirm()
        line0, line1 = so.order_line[0], so.order_line[1]
        # Nota: según la config del entorno, los pasos internos pueden fusionarse entre
        # líneas (un move de 20) o no. El invariante que importa vale en ambos casos:
        # cancelar una línea NO debe romper la otra.

        line0.button_cancel_remaining()
        self.assertTrue(
            float_is_zero(line0.product_uom_qty, precision_digits=2), "H: la línea cancelada debe quedar en 0"
        )
        self.assertEqual(
            float_compare(line1.product_uom_qty, 10.0, precision_digits=2),
            0,
            "H: la cantidad de la otra línea NO se debe tocar",
        )
        # la línea 1 debe poder entregarse COMPLETA (su cadena no fue cancelada)
        for _i in range(6):
            picking = so.picking_ids.filtered(lambda p: p.state == "assigned").sorted("id")[:1]
            if not picking:
                break
            self._deliver(picking)
        self.assertEqual(
            float_compare(line1.qty_delivered, 10.0, precision_digits=2),
            0,
            "H: la línea no cancelada quedó sin poder entregarse (qty_delivered=%s), "
            "se canceló un move fusionado compartido" % line1.qty_delivered,
        )
        self.assertTrue(
            float_is_zero(line0.qty_delivered, precision_digits=2), "H: la línea cancelada no debería entregar nada"
        )

    # ---------------- Escenario I: UoM distinta (docenas) ----------------
    def test_I_uom_docenas(self):
        """La línea vendida en docenas: la reducción y el retorno de tránsito deben
        respetar la conversión de UoM (no dejar cantidades mal convertidas)."""
        dozen = self.env.ref("uom.product_uom_dozen")
        product = self._product("I")  # uom_id = unidades
        product.route_ids = [(6, 0, self.mto3.ids)]
        self._stock(product, self.wh3.lot_stock_id)
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.wh3.id,
                "order_line": [(0, 0, {"product_id": product.id, "product_uom_qty": 10.0, "product_uom": dozen.id})],
            }
        )
        so.action_confirm()
        self._deliver(self._next_picking(so))  # PICK 10 docenas -> Packing
        so.order_line.button_cancel_remaining()
        self._assert_clean_cancel(so, 0.0, "I docenas PICK full")

    # ---------------- Escenario J: orden bloqueada ----------------
    def test_J_orden_bloqueada(self):
        so = self._confirm(self._product("J"), self.wh3, route=self.mto3)
        self._deliver(self._next_picking(so))
        so.action_lock()
        self.assertTrue(so.locked, "J: la orden debería estar bloqueada")
        so.order_line.button_cancel_remaining()
        self.assertTrue(so.locked, "J: la orden debe volver a quedar bloqueada")
        self._assert_clean_cancel(so, 0.0, "J orden bloqueada")

    # ---------------- Escenario K: con devolución previa del cliente ----------------
    def test_K_con_devolucion_previa(self):
        """Si hubo devolución real del cliente, el target = entregado + devuelto.
        Entregamos 10, el cliente devuelve 3 -> quedan 7 'netos'. Cancelar remanente
        no debe romper nada (la línea ya está full entregada)."""
        so = self._confirm(self._product("K"), self.wh1)  # 1 paso, simple
        self._deliver(self._next_picking(so))  # entrega 10 al cliente
        line = so.order_line
        self.assertEqual(float_compare(line.qty_delivered, 10.0, precision_digits=2), 0)
        # devolución del cliente por 3
        return_wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=so.picking_ids.id, active_model="stock.picking", active_ids=so.picking_ids.ids)
            .create({"picking_id": so.picking_ids.id})
        )
        for rline in return_wizard.product_return_moves:
            rline.quantity = 3.0
        action = return_wizard.action_create_returns()
        ret_picking = self.env["stock.picking"].browse(action["res_id"])
        self._deliver(ret_picking)
        self.assertEqual(
            float_compare(line.quantity_returned, 3.0, precision_digits=2),
            0,
            "K: la devolución del cliente debería contar como returned",
        )
        # cancelar remanente: target = 10 entregado - 3 devuelto ... = qty_delivered(7)+returned(3)=10
        so.order_line.button_cancel_remaining()
        self.assertEqual(
            float_compare(line.product_uom_qty, 10.0, precision_digits=2),
            0,
            "K: la línea debe reflejar entregado+devuelto",
        )

    # ---------------- Escenario L: ticket 122867 ----------------
    def test_L_122867_usuario_sin_permiso_cancelar_picking(self):
        """Ticket 122867 (base brunetti, 1 paso): el usuario que cancela remanente NO
        tiene el permiso 'Picking cancelation allow' de stock_ux, y el picking ya está
        reservado e IMPRESO. Con el enfoque de delegar, la entrega no se ponía en 0 y
        el OUT quedaba entregable (se despachó de más). El fix debe:
          - no explotar con el constraint check_cancel (cancela vía cancel_from_order),
          - dejar el OUT cancelado (cantidad 0 en la entrega),
          - y funcionar para un usuario NO administrador de stock."""
        self.assertFalse(
            self.restricted_user.has_group("stock_ux.allow_picking_cancellation"),
            "L: el usuario de prueba no debería tener el permiso de cancelar pickings",
        )
        product = self._product("L")
        self._stock(product, self.wh1.lot_stock_id)
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.wh1.id,
                "user_id": self.restricted_user.id,
                "order_line": [(0, 0, {"product_id": product.id, "product_uom_qty": 5.0})],
            }
        )
        so.action_confirm()
        picking = so.picking_ids
        picking.move_ids._action_assign()  # reservar
        for move in picking.move_ids:
            move.move_line_ids.unlink()
            move.quantity = 5.0
            move.picked = True
        picking.printed = True  # picking impreso (trigger del ticket)

        # cancelar remanente COMO el usuario restringido (no admin de stock)
        so.order_line.with_user(self.restricted_user).button_cancel_remaining()

        line = so.order_line
        self.assertTrue(float_is_zero(line.product_uom_qty, precision_digits=2), "L: la línea debe quedar en 0")
        out_moves = so.picking_ids.mapped("move_ids")
        deliverable = out_moves.filtered(
            lambda m: m.state not in ("done", "cancel") and m.location_dest_id.usage == "customer" and m.quantity > 0
        )
        self.assertFalse(
            deliverable,
            "L: no debe quedar entrega pendiente con cantidad (la mercadería "
            "se despacharía de más): %s" % [(m.id, m.state, m.quantity) for m in deliverable],
        )

    # ---------------- Escenario M: multi-línea fusionada CON tránsito done ----------------
    def test_M_multilinea_transito_no_sobredevuelve(self):
        """2 líneas mismo producto, MTO 3 pasos, PICK+PACK validados (fusionados, 20 en
        Output). Cancelar UNA línea debe devolver a Stock solo SU parte (10), no el
        tránsito de la otra línea (20). El retorno se topea en el remanente de la línea."""
        product = self._product("M")
        product.route_ids = [(6, 0, self.mto3.ids)]
        self._stock(product, self.wh3.lot_stock_id)
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.wh3.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": 10.0}),
                    (0, 0, {"product_id": product.id, "product_uom_qty": 10.0}),
                ],
            }
        )
        so.action_confirm()
        self._deliver(self._next_picking(so))  # PICK 20 -> Packing (fusionado)
        self._deliver(self._next_picking(so))  # PACK 20 -> Output (fusionado)
        so.order_line[0].button_cancel_remaining()
        returned = sum(
            so.picking_ids.mapped("move_ids")
            .filtered(lambda m: m.location_dest_id == self.wh3.lot_stock_id and m.state != "cancel")
            .mapped("product_uom_qty")
        )
        self.assertEqual(
            float_compare(returned, 10.0, precision_digits=2),
            0,
            "M: debe devolver 10 (parte de la línea cancelada), no %s (roba tránsito de la otra línea)" % returned,
        )
        # la otra línea sigue con sus 10 en tránsito hacia el cliente
        self.assertEqual(float_compare(so.order_line[1].product_uom_qty, 10.0, precision_digits=2), 0)
