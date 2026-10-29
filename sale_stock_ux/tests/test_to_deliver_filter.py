from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestToDeliverFilter(TransactionCase):
    """El filtro nativo "To Deliver" (is_unfulfilled) y la tarjeta del tablero usan el estado
    de entrega del módulo: descuentan las devoluciones y respetan el estado forzado."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "Test To Deliver", "type": "consu", "is_storable": True, "invoice_policy": "order"}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test To Deliver Partner", "customer_rank": 1})
        warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.env["stock.quant"]._update_available_quantity(cls.product, warehouse.lot_stock_id, 100.0)
        if cls.env["sale.order"]._fields.get("ignore_exception"):
            cls.env["exception.rule"].search([("active", "=", True)]).write({"active": False})

    def _new_order(self, qty=10):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": qty, "price_unit": 10.0})],
            }
        )
        order.action_confirm()
        return order

    def _validate(self, picking, qty=None):
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty if qty is None else qty
        picking.move_ids.picked = True
        picking.with_context(cancel_backorder=True)._action_done()

    def _to_deliver(self, order):
        return order in self.env["sale.order"].search([("is_unfulfilled", "=", True), ("id", "=", order.id)])

    def test_pending_delivery_is_to_deliver(self):
        order = self._new_order()
        self.assertTrue(self._to_deliver(order))
        self._validate(order.picking_ids, qty=4)
        self.assertTrue(self._to_deliver(order))

    def test_return_with_credit_note_is_not_to_deliver(self):
        """Entregar 10 y devolver 2 para abonar: la venta no está para entregar (el nativo la mostraba)."""
        order = self._new_order()
        delivery = order.picking_ids
        self._validate(delivery)
        returned = self.env["stock.picking"].browse(delivery.action_return()["res_id"])
        returned.move_ids.product_uom_qty = 2
        self._validate(returned)
        self.assertEqual(order.order_line.qty_delivered, 8.0)
        self.assertFalse(self._to_deliver(order))

    def test_forced_delivered_is_not_to_deliver(self):
        order = self._new_order()
        order.force_delivery_status = "full"
        self.assertFalse(self._to_deliver(order))
        self.assertIn(order, self.env["sale.order"].search([("is_unfulfilled", "=", False), ("id", "=", order.id)]))
