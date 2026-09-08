##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPhantomCounterdelivery(TransactionCase):
    """Detección + aviso + saneo manual de contra-entregas fantasma (tarea 73048).

    El quiebre del merge que *genera* el fantasma ya lo cubre
    `test_cancel_remaining_push_domain`. Acá probamos la capa v1 que reacciona
    al artefacto: un movimiento invertido (Cliente -> interno), vivo, con
    `to_refund` y sin `origin_returned_move_id`, se detecta, levanta actividad y
    se puede sanear a mano — sin tocar nada automáticamente.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer_loc = cls.env.ref("stock.stock_location_customers")
        cls.stock_loc = cls.env.ref("stock.stock_location_stock")
        cls.partner = cls.env["res.partner"].create({"name": "Phantom Customer"})
        cls.product = cls.env["product.product"].create(
            {"name": "Phantom Product", "type": "consu", "is_storable": True}
        )
        cls.picking_type_out = cls.env.ref("stock.picking_type_out")
        # Beta opt-in: habilitamos el parametro para ejercitar el flujo.
        cls.env["ir.config_parameter"].sudo().set_param("sale_stock_ux.sanity_pickings", "True")
        # El saneo requiere permiso maximo de inventario.
        cls.env.user.groups_id = [(4, cls.env.ref("stock.group_stock_manager").id)]

    def _make_confirmed_order(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 2.0})],
            }
        )
        order.action_confirm()
        return order

    def _inject_phantom_move(self, order):
        """Materializa una contra-entrega fantasma en un picking del pedido."""
        picking = self.env["stock.picking"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.picking_type_out.id,
                "location_id": self.customer_loc.id,
                "location_dest_id": self.stock_loc.id,
                "group_id": order.procurement_group_id.id,
                "sale_id": order.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "name": self.product.name,
                "product_id": self.product.id,
                "product_uom_qty": 1.0,
                "product_uom": self.product.uom_id.id,
                "location_id": self.customer_loc.id,
                "location_dest_id": self.stock_loc.id,
                "picking_id": picking.id,
                "sale_line_id": order.order_line[0].id,
                "to_refund": True,
            }
        )
        move._action_confirm()
        order.invalidate_recordset()
        return move

    def test_no_false_positive_on_clean_order(self):
        order = self._make_confirmed_order()
        self.assertFalse(order._detect_phantom_counterdeliveries())
        self.assertFalse(order.has_phantom_counterdelivery)

    def test_detects_and_notifies(self):
        order = self._make_confirmed_order()
        move = self._inject_phantom_move(order)

        self.assertIn(move, order._detect_phantom_counterdeliveries())
        self.assertTrue(order.has_phantom_counterdelivery)

        order._notify_phantom_counterdeliveries()
        acts = order.activity_ids.filtered(lambda a: a.summary == "Posible(s) contra-entrega(s) fantasma")
        self.assertEqual(len(acts), 1, "Debe levantar una actividad de aviso")

        # idempotente: no duplica la actividad
        order._notify_phantom_counterdeliveries()
        acts = order.activity_ids.filtered(lambda a: a.summary == "Posible(s) contra-entrega(s) fantasma")
        self.assertEqual(len(acts), 1, "No debe duplicar la actividad abierta")

    def test_beta_gate_off_hides_button_and_skips_notify(self):
        """Con el parametro beta apagado, no se enciende el boton ni se avisa,
        aunque exista un fantasma. La deteccion pura sigue disponible."""
        self.env["ir.config_parameter"].sudo().set_param("sale_stock_ux.sanity_pickings", "False")
        order = self._make_confirmed_order()
        move = self._inject_phantom_move(order)

        self.assertIn(move, order._detect_phantom_counterdeliveries(), "la deteccion pura no se gatea")
        self.assertFalse(order.has_phantom_counterdelivery, "el boton queda oculto con beta off")

        order._notify_phantom_counterdeliveries()
        acts = order.activity_ids.filtered(lambda a: a.summary == "Posible(s) contra-entrega(s) fantasma")
        self.assertFalse(acts, "no debe avisar con beta off")

    def test_search_filter(self):
        """El filtro (search method) encuentra la orden con fantasma sin campo
        stored, y la excluye cuando el beta esta apagado."""
        order = self._make_confirmed_order()
        self._inject_phantom_move(order)

        found = self.env["sale.order"].search([("has_phantom_counterdelivery", "=", True)])
        self.assertIn(order, found)
        not_found = self.env["sale.order"].search([("has_phantom_counterdelivery", "=", False)])
        self.assertNotIn(order, not_found)

        # beta off -> el filtro no matchea nada
        self.env["ir.config_parameter"].sudo().set_param("sale_stock_ux.sanity_pickings", "False")
        found_off = self.env["sale.order"].search([("has_phantom_counterdelivery", "=", True)])
        self.assertNotIn(order, found_off)

    def test_sanitize_requires_stock_manager(self):
        """Sin permiso máximo de inventario, el saneo no se puede ejecutar."""
        order = self._make_confirmed_order()
        self._inject_phantom_move(order)
        user = self.env["res.users"].create(
            {
                "name": "Sale only",
                "login": "phantom_sale_only",
                "groups_id": [(6, 0, [self.env.ref("sales_team.group_sale_salesman").id])],
            }
        )
        with self.assertRaises(AccessError):
            order.with_user(user).action_sanitize_phantom_counterdeliveries()

    def test_genuine_return_is_not_flagged(self):
        """Una devolución genuina (con origin_returned_move_id) NO es fantasma."""
        order = self._make_confirmed_order()
        move = self._inject_phantom_move(order)
        # simulamos que es una devolución real: apunta a un move de salida origen
        origin = order.picking_ids.move_ids.filtered(lambda m: m.location_dest_id.usage == "customer")[:1]
        move.origin_returned_move_id = origin.id if origin else move.id
        self.assertNotIn(move, order._detect_phantom_counterdeliveries())

    def test_manual_sanitize_cancels_only_phantom(self):
        order = self._make_confirmed_order()
        move = self._inject_phantom_move(order)
        legit = order.picking_ids.move_ids.filtered(lambda m: m.location_dest_id.usage == "customer")

        order.action_sanitize_phantom_counterdeliveries()

        self.assertEqual(move.state, "cancel", "El fantasma debe quedar cancelado")
        self.assertTrue(
            all(m.state != "cancel" for m in legit),
            "El saneo no debe tocar los movimientos legítimos del pedido",
        )
        self.assertFalse(order.has_phantom_counterdelivery)

    # ---- caso real multi-paso (ticket 127204 / OV 0001-00190946) ---------
    # El fantasma real no es un move suelto: es una cadena inversa (Cliente->
    # Despacho + patas internas de put-back) toda to_refund, y puede dejar una
    # cadena forward espuria. El saneo debe barrer todo el footprint.

    def _make_internal_locs(self):
        parent = self.stock_loc.location_id
        despacho = self.env["stock.location"].create(
            {"name": "PH Despacho", "usage": "internal", "location_id": parent.id}
        )
        pack = self.env["stock.location"].create({"name": "PH Pack", "usage": "internal", "location_id": parent.id})
        return despacho, pack

    def _inject_move(
        self,
        order,
        src,
        dest,
        to_refund=True,
        origin=None,
        qty=1.0,
        done=False,
        sale_line=True,
        prev=None,
        product=None,
        line=None,
    ):
        product = product or self.product
        picking = self.env["stock.picking"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.picking_type_out.id,
                "location_id": src.id,
                "location_dest_id": dest.id,
                "group_id": order.procurement_group_id.id,
                "sale_id": order.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "name": product.name,
                "product_id": product.id,
                "product_uom_qty": qty,
                "product_uom": product.uom_id.id,
                "location_id": src.id,
                "location_dest_id": dest.id,
                "picking_id": picking.id,
                "sale_line_id": (line or order.order_line[0]).id if sale_line else False,
                "to_refund": to_refund,
            }
        )
        if origin:
            move.origin_returned_move_id = origin.id
        move._action_confirm()
        # Encadenamiento: la cadena inversa real cuelga de la entrada fantasma por
        # move_orig_ids/move_dest_ids. `prev` es el move del que este es continuacion.
        if prev:
            move.move_orig_ids = [(4, prev.id)]
        if done:
            move.quantity = qty
            move.picked = True
            move._action_done()
        order.invalidate_recordset()
        return move

    def test_sanitize_cancels_full_reverse_chain(self):
        """La cadena inversa completa (DEVC + patas internas to_refund ENCADENADAS)
        se cancela; una devolución genuina (origin_returned) NO se toca.

        El fantasma real es una cadena encadenada (DEVC -> put-back PACK -> put-back
        PICK por move_orig/move_dest), no moves sueltos que compartan solo el grupo:
        el saneo la recorre desde la entrada."""
        despacho, pack = self._make_internal_locs()
        order = self._make_confirmed_order()  # qty 2, demanda pendiente
        devc = self._inject_move(order, self.customer_loc, despacho, to_refund=True)
        rev_pack = self._inject_move(order, despacho, pack, to_refund=True, sale_line=False, prev=devc)
        rev_pick = self._inject_move(order, pack, self.stock_loc, to_refund=True, sale_line=False, prev=rev_pack)
        genuine = self._inject_move(order, self.customer_loc, self.stock_loc, to_refund=True, origin=devc)

        order.action_sanitize_phantom_counterdeliveries()

        self.assertEqual(devc.state, "cancel", "el DEVC Cliente->interno debe cancelarse")
        self.assertEqual(rev_pack.state, "cancel", "la pata inversa PACK debe cancelarse")
        self.assertEqual(rev_pick.state, "cancel", "la pata inversa PICK debe cancelarse")
        self.assertNotEqual(genuine.state, "cancel", "la devolución genuina NO debe tocarse")

    def test_sanitize_keeps_legit_putback_of_other_line(self):
        """Regresión: un put-back interno legítimo de OTRA línea (devolver a Stock lo
        ya movido) también es to_refund, pero cuelga de su propia cadena, sin entrada
        Cliente->interno. El saneo NO debe cancelarlo aunque coexista con un fantasma
        en el mismo grupo (si no, vararía stock en silencio)."""
        despacho, pack = self._make_internal_locs()
        product_b = self.env["product.product"].create(
            {"name": "Phantom Product B", "type": "consu", "is_storable": True}
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 2.0}),
                    (0, 0, {"product_id": product_b.id, "product_uom_qty": 2.0}),
                ],
            }
        )
        order.action_confirm()
        line_b = order.order_line.filtered(lambda line: line.product_id == product_b)
        # fantasma de la línea A: entrada + pata inversa encadenada
        devc = self._inject_move(order, self.customer_loc, despacho, to_refund=True)
        rev = self._inject_move(order, despacho, self.stock_loc, to_refund=True, sale_line=False, prev=devc)
        # put-back legítimo de la línea B: interno->interno, to_refund, SIN encadenar
        # a la entrada fantasma (su propio componente del grafo).
        legit_b = self._inject_move(order, pack, self.stock_loc, to_refund=True, product=product_b, line=line_b)

        order.action_sanitize_phantom_counterdeliveries()

        self.assertEqual(devc.state, "cancel", "el fantasma A debe cancelarse")
        self.assertEqual(rev.state, "cancel", "la pata inversa A debe cancelarse")
        self.assertNotEqual(legit_b.state, "cancel", "el put-back legítimo de B NO debe tocarse (evitar varar stock)")

    def test_sanitize_cancels_forward_spurious_when_no_demand(self):
        """Sin demanda restante del producto, la cadena forward espuria también
        se barre (además de la inversa)."""
        despacho, _pack = self._make_internal_locs()
        order = self._make_confirmed_order()  # qty 2
        self._inject_move(order, self.stock_loc, self.customer_loc, to_refund=False, qty=2.0, done=True)
        self.assertEqual(order.order_line[0].qty_delivered, 2.0, "precondición: entregado 2 -> demanda 0")
        devc = self._inject_move(order, self.customer_loc, despacho, to_refund=True)
        forward = self._inject_move(order, self.stock_loc, self.customer_loc, to_refund=False, qty=1.0)

        order.action_sanitize_phantom_counterdeliveries()

        self.assertEqual(devc.state, "cancel")
        self.assertEqual(forward.state, "cancel", "forward espuria (producto sin demanda) debe cancelarse")

    def test_sanitize_keeps_forward_with_remaining_demand(self):
        """Con demanda pendiente, solo se barre la cadena inversa to_refund; una
        entrega forward pendiente legítima NO se cancela."""
        despacho, _pack = self._make_internal_locs()
        order = self._make_confirmed_order()  # qty 2, demanda pendiente
        devc = self._inject_move(order, self.customer_loc, despacho, to_refund=True)
        forward = self._inject_move(order, self.stock_loc, self.customer_loc, to_refund=False, qty=1.0)

        order.action_sanitize_phantom_counterdeliveries()

        self.assertEqual(devc.state, "cancel", "el fantasma to_refund se cancela")
        self.assertNotEqual(forward.state, "cancel", "con demanda pendiente, el forward NO se toca")

    def _drop_beta_param(self):
        """Deja la base como una que nunca creó el parámetro (no 'False': ausente)."""
        self.env["ir.config_parameter"].sudo().search([("key", "=", "sale_stock_ux.sanity_pickings")]).unlink()

    def _salesman(self):
        return self.env["res.users"].create(
            {
                "name": "Phantom Salesman",
                "login": "phantom_no_stock_rights",
                "groups_id": [(6, 0, [self.env.ref("sales_team.group_sale_salesman").id])],
            }
        )

    def test_param_absent_hides_everything_for_both_permission_levels(self):
        """Sin el parámetro creado, el pedido con fantasma no muestra NINGÚN
        aviso: ni para el vendedor (banner pelado) ni para el administrador de
        inventario (banner + botón). La beta es indetectable hasta habilitarla."""
        order = self._make_confirmed_order()
        self._inject_phantom_move(order)
        self._drop_beta_param()
        order.invalidate_recordset()

        # el gate lee "ausente" como apagado, no como activo
        self.assertFalse(order._phantom_beta_enabled())

        # nivel 1: vendedor sin permisos de inventario -> banner invisible
        salesman = self._salesman()
        self.assertFalse(order.with_user(salesman).has_phantom_counterdelivery)

        # nivel 2: administrador de inventario -> banner y botón invisibles
        self.assertTrue(self.env.user.has_group("stock.group_stock_manager"))
        self.assertFalse(order.has_phantom_counterdelivery)

        # y no se avisa por actividad al cancelar remanente
        order._notify_phantom_counterdeliveries()
        self.assertFalse(
            order.activity_ids.filtered(lambda a: a.summary == self.env["sale.order"]._phantom_activity_summary())
        )

    def test_param_absent_blocks_sanitize_even_for_stock_manager(self):
        """El saneo no es alcanzable por RPC con la beta sin habilitar, aunque
        el usuario tenga el permiso máximo de inventario."""
        order = self._make_confirmed_order()
        self._inject_phantom_move(order)
        self._drop_beta_param()

        with self.assertRaises(UserError):
            order.action_sanitize_phantom_counterdeliveries()

    def test_param_absent_filter_returns_nothing(self):
        """El filtro tampoco delata pedidos con la beta sin habilitar."""
        order = self._make_confirmed_order()
        self._inject_phantom_move(order)
        self._drop_beta_param()

        found = self.env["sale.order"].search([("has_phantom_counterdelivery", "=", True)])
        self.assertNotIn(order, found)
