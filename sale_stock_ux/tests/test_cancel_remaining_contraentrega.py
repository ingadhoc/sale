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
