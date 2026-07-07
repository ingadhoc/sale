from odoo.tests import TransactionCase


class TestCancelRemainingContraentrega(TransactionCase):
    """Regresión ticket 121400.

    Al cancelar el remanente de una línea NO entregada cuya salida fue reservada
    desde una sub-ubicación distinta al origen nominal de la regla de stock, NO
    debe generarse una contraentrega (movimiento inverso / picking de entrada
    fantasma) ni dejar el movimiento de salida huérfano comprometiendo stock.
    """

    def setUp(self):
        super().setUp()
        self.product = self.env["product.product"].create(
            {"name": "Test Product 121400", "list_price": 100.0, "type": "consu"}
        )
        self.partner = self.env["res.partner"].create({"name": "Test Partner 121400", "customer_rank": 1})

        # Desactivar reglas de excepción si el módulo está instalado (evita error en runbot)
        if self.env["sale.order"]._fields.get("ignore_exception"):
            self.env["exception.rule"].search([("active", "=", True)]).write({"active": False})

    def test_cancel_remaining_no_contraentrega_from_sublocation(self):
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)

        # Sub-ubicación bajo el stock del depósito (simula Caballito/Gargano de vreme)
        sub_location = self.env["stock.location"].create(
            {
                "name": "Sub Stock 121400",
                "usage": "internal",
                "location_id": warehouse.lot_stock_id.id,
            }
        )

        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 10, "price_unit": 100.0})],
            }
        )
        sale_order.action_confirm()

        line = sale_order.order_line
        out_move = line.move_ids
        self.assertEqual(len(out_move), 1)
        self.assertNotIn(out_move.state, ("done", "cancel"))

        # Gatillo del bug: la salida tiene como origen una sub-ubicación distinta
        # al origen nominal de la regla (warehouse.lot_stock_id). Eso hace que el
        # movimiento negativo del recálculo no se fusione con el move original.
        out_move.write({"location_id": sub_location.id})

        # Cancelar remanente (nada entregado)
        line.with_context(cancel_from_order=True).button_cancel_remaining()

        # 1) La línea baja a lo entregado (0)
        self.assertEqual(line.product_uom_qty, 0.0)
        # 2) El movimiento de salida quedó cancelado (no huérfano en 'confirmed')
        self.assertEqual(out_move.state, "cancel")
        # 3) NO se generó contraentrega: ningún picking de entrada en la orden
        incoming = sale_order.picking_ids.filtered(lambda p: p.picking_type_code == "incoming")
        self.assertFalse(incoming, "No debe generarse una contraentrega (picking de entrada)")
        # 4) NO hay movimientos vivos saliendo del cliente (el move inverso fantasma)
        phantom = line.move_ids.filtered(lambda m: m.state != "cancel" and m.location_id.usage == "customer")
        self.assertFalse(phantom, "No debe existir un movimiento inverso (contraentrega)")

    def _validate_all_live_pickings(self, sale_order):
        """Valida (sin backorder) todos los pickings vivos de la orden, iterando
        hasta que no quede ninguno pendiente. Simula el operario completando la
        contraentrega legítima que devuelve el stock en tránsito al origen."""
        for _ in range(6):
            live = sale_order.picking_ids.filtered(lambda p: p.state not in ("done", "cancel"))
            if not live:
                break
            for picking in live:
                picking.action_assign()
                for move in picking.move_ids.filtered(lambda m: m.state not in ("done", "cancel")):
                    move.quantity = move.product_uom_qty
                    move.picked = True
                res = picking.button_validate()
                if isinstance(res, dict) and res.get("res_model") == "stock.backorder.confirmation":
                    wiz = self.env[res["res_model"]].with_context(**res["context"]).create({})
                    wiz.process_cancel_backorder()

    def _transit_qty(self, product, warehouse):
        """Cantidad del producto parada en ubicaciones internas intermedias
        (Output / Packing Zone), es decir internas pero fuera del stock raíz."""
        root = warehouse.lot_stock_id
        quants = self.env["stock.quant"].search(
            [("product_id", "=", product.id), ("location_id.usage", "=", "internal")]
        )
        total = 0.0
        for quant in quants:
            loc = quant.location_id
            under_root = loc == root or ("/%d/" % root.id) in (loc.parent_path or "")
            if not under_root:
                total += quant.quantity
        return total

    def test_cancel_remaining_two_steps_no_stranded_stock(self):
        """Regresión de la regresión (ticket 121400, entregas multi-paso).

        En una entrega en dos pasos (PICK + OUT), si el PICK ya se validó, la
        mercadería quedó en la zona de salida (Output). Al cancelar el remanente,
        el método debe generar la contraentrega legítima que devuelve ese stock
        en tránsito al origen; NO debe dejarlo varado en Output.

        Este test falla con el approach de "cancelar moves pendientes +
        skip_procurement" aplicado indiscriminadamente (mata el reverso legítimo)
        y pasa con el discriminador por stock en tránsito.
        """
        storable = self.env["product.product"].create(
            {"name": "Test Product 121400 2steps", "list_price": 100.0, "type": "consu", "is_storable": True}
        )
        warehouse = self.env["stock.warehouse"].create(
            {"name": "WH 121400 2steps", "code": "T21", "company_id": self.env.company.id}
        )
        warehouse.delivery_steps = "pick_ship"

        self.env["stock.quant"].with_context(inventory_mode=True)._update_available_quantity(
            storable, warehouse.lot_stock_id, 100
        )

        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": warehouse.id,
                "order_line": [(0, 0, {"product_id": storable.id, "product_uom_qty": 10, "price_unit": 100.0})],
            }
        )
        sale_order.action_confirm()
        line = sale_order.order_line

        # Validar completo el PICK -> 10 unidades quedan en Output (en tránsito)
        pick = sale_order.picking_ids.filtered(lambda p: p.picking_type_id.sequence_code == "PICK")
        pick.action_assign()
        for move in pick.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        pick.button_validate()
        self.assertEqual(self._transit_qty(storable, warehouse), 10.0, "El PICK debió dejar 10 en Output")

        # Cancelar remanente (nada llegó al cliente todavía)
        line.with_context(cancel_from_order=True).button_cancel_remaining()
        self.assertEqual(line.product_uom_qty, 0.0)

        # Completar los movimientos vivos (la contraentrega/retorno legítimo)
        self._validate_all_live_pickings(sale_order)

        # El stock en tránsito NO debe quedar varado en Output: debe volver al origen
        self.assertEqual(
            self._transit_qty(storable, warehouse),
            0.0,
            "No debe quedar stock varado en Output tras cancelar el remanente en multi-paso",
        )

    def _build_three_step_mto_route(self, warehouse):
        """Ruta de entrega en 3 pasos PULL/MTO encadenada (PICK->PACK->OUT), como
        la que usa Cedent: los 3 moves se crean encadenados al confirmar la orden
        y `sale_line_id` queda SOLO en el move OUT. La ruta auto-generada del
        warehouse de test arma los pasos por reglas push (progresivas), que no
        reproducen el escenario."""
        customer_loc = self.env.ref("stock.stock_location_customers")
        route = self.env["stock.route"].create(
            {"name": "R122299 3 pasos MTO", "product_selectable": True}
        )
        steps = [
            ("pick", warehouse.lot_stock_id, warehouse.wh_pack_stock_loc_id, warehouse.pick_type_id, "make_to_stock"),
            ("pack", warehouse.wh_pack_stock_loc_id, warehouse.wh_output_stock_loc_id, warehouse.pack_type_id, "make_to_order"),
            ("out", warehouse.wh_output_stock_loc_id, customer_loc, warehouse.out_type_id, "make_to_order"),
        ]
        for name, src, dst, ptype, procure_method in steps:
            self.env["stock.rule"].create(
                {
                    "name": name,
                    "route_id": route.id,
                    "action": "pull",
                    "picking_type_id": ptype.id,
                    "location_src_id": src.id,
                    "location_dest_id": dst.id,
                    "procure_method": procure_method,
                    "warehouse_id": warehouse.id,
                }
            )
        return route

    def test_cancel_remaining_three_steps_no_orphan_upstream_demand(self):
        """Regresión ticket 122299 (Cedent, entrega en 3 pasos).

        Ruta PICK -> PACK -> OUT pull/MTO (cadena creada al confirmar). Nada
        entregado. Al cancelar el remanente, la línea baja a 0 y el move OUT se
        cancela, PERO los PICK/PACK aguas arriba quedan vivos demandando la
        cantidad original: el depósito prepara de más (exactamente lo reportado
        — el pick pide más que la OV).

        Causa: button_cancel_remaining solo actúa sobre `line.move_ids`, que en
        multi-paso son los OUT (los PICK/PACK tienen sale_line_id=False), y nada
        recorre la cadena aguas arriba. La propagación nativa de Odoo
        (`propagate_cancel`) va aguas ABAJO (move_dest_ids), así que cancelar el
        OUT nunca limpia el PICK/PACK, tenga el flag el valor que tenga. No
        depende de config del cliente: pasa en cualquier entrega multi-paso MTO.
        """
        storable = self.env["product.product"].create(
            {"name": "Test Product 122299 3steps", "list_price": 100.0, "type": "consu", "is_storable": True}
        )
        warehouse = self.env["stock.warehouse"].create(
            {"name": "WH 122299 3steps", "code": "T22", "company_id": self.env.company.id}
        )
        warehouse.delivery_steps = "pick_pack_ship"
        route = self._build_three_step_mto_route(warehouse)
        storable.route_ids = [(6, 0, route.ids)]

        self.env["stock.quant"].with_context(inventory_mode=True)._update_available_quantity(
            storable, warehouse.lot_stock_id, 100
        )

        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": warehouse.id,
                "order_line": [(0, 0, {"product_id": storable.id, "product_uom_qty": 20, "price_unit": 100.0})],
            }
        )
        sale_order.action_confirm()
        line = sale_order.order_line

        # Cadena completa creada al confirmar: PICK + PACK + OUT, sale_line_id solo en OUT.
        all_moves = sale_order.picking_ids.move_ids.filtered(lambda m: m.product_id == storable)
        self.assertEqual(len(all_moves), 3, "Se esperaba la cadena PICK + PACK + OUT")
        self.assertEqual(
            all_moves.filtered(lambda m: m.sale_line_id).mapped("picking_id.picking_type_id.sequence_code"),
            ["OUT"],
            "sale_line_id debe estar solo en el move OUT (como en Cedent)",
        )

        # Cancelar remanente (nada llegó al cliente todavía)
        line.with_context(cancel_from_order=True).button_cancel_remaining()
        self.assertEqual(line.product_uom_qty, 0.0)

        # --- Demanda huérfana aguas arriba ---
        live = all_moves.filtered(lambda m: m.state not in ("done", "cancel"))
        self.assertFalse(
            live,
            "Quedaron moves vivos aguas arriba (PICK/PACK) tras cancelar el remanente "
            "en 3 pasos con propagate_cancel=False: el depósito prepararía de más "
            "(ticket 122299). Moves vivos: %s"
            % [(m.picking_id.name, m.product_uom_qty, m.state) for m in live],
        )

    def test_cancel_remaining_three_steps_partial_pick_no_orphan(self):
        """Regresión ticket 122299 (caso 'Negro': 3 pasos con PICK PARCIAL).

        Ruta PICK -> PACK -> OUT pull/MTO. El PICK se valida parcialmente: parte
        queda EN TRÁNSITO (pack loc) y se genera un backorder por el remanente.
        Al cancelar el remanente:
          - el stock en tránsito ya pickeado debe volver al origen (contraentrega),
          - el remanente NO pickeado aguas arriba (PICK backorder + su PACK) NO debe
            quedar vivo demandando de más.
        Este es el caso rama (a) de button_cancel_remaining.
        """
        storable = self.env["product.product"].create(
            {"name": "Test Product 122299 partial", "list_price": 100.0, "type": "consu", "is_storable": True}
        )
        warehouse = self.env["stock.warehouse"].create(
            {"name": "WH 122299 partial", "code": "T23", "company_id": self.env.company.id}
        )
        warehouse.delivery_steps = "pick_pack_ship"
        route = self._build_three_step_mto_route(warehouse)
        storable.route_ids = [(6, 0, route.ids)]

        self.env["stock.quant"].with_context(inventory_mode=True)._update_available_quantity(
            storable, warehouse.lot_stock_id, 100
        )

        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": warehouse.id,
                "order_line": [(0, 0, {"product_id": storable.id, "product_uom_qty": 20, "price_unit": 100.0})],
            }
        )
        sale_order.action_confirm()
        line = sale_order.order_line

        # Validar PARCIALMENTE el PICK: 10 de 20 -> 10 en tránsito (pack loc) + backorder 10.
        pick = sale_order.picking_ids.filtered(lambda p: p.picking_type_id.sequence_code == "PICK")
        pick.action_assign()
        pick.move_ids.quantity = 10
        pick.move_ids.picked = True
        res = pick.button_validate()
        if isinstance(res, dict) and res.get("res_model") == "stock.backorder.confirmation":
            wiz = self.env[res["res_model"]].with_context(**res["context"]).create({})
            wiz.process()  # crear backorder por el remanente
        self.assertEqual(self._transit_qty(storable, warehouse), 10.0, "El PICK parcial debió dejar 10 en tránsito")

        # Cancelar remanente
        line.with_context(cancel_from_order=True).button_cancel_remaining()
        self.assertEqual(line.product_uom_qty, 0.0)

        # 1) No debe quedar remanente pendiente demandando de más.
        backorder_pick = sale_order.picking_ids.filtered(
            lambda p: p.picking_type_id.sequence_code == "PICK" and p.backorder_id
        )
        live_backorder = backorder_pick.move_ids.filtered(lambda m: m.state not in ("done", "cancel"))
        self.assertFalse(
            live_backorder,
            "El PICK backorder del remanente quedó vivo tras cancelar el remanente (ticket 122299)",
        )

        # 2) El stock en tránsito debe volver al origen (no quedar varado).
        self._validate_all_live_pickings(sale_order)
        self.assertEqual(
            self._transit_qty(storable, warehouse),
            0.0,
            "El stock en tránsito no volvió al origen tras cancelar el remanente (caso parcial 122299)",
        )
