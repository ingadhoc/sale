from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCancelRemainingLostQty(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "Cancel Remaining Product", "list_price": 100.0, "type": "consu", "is_storable": True}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Cancel Remaining Partner", "customer_rank": 1})
        cls.lost_reason = cls.env["sale.order.line.lost.reason"].create({"name": "Out of stock"})

        # evita que las reglas de excepción corten la confirmación en runbot
        if cls.env["sale.order"]._fields.get("ignore_exception"):
            cls.env["exception.rule"].search([("active", "=", True)]).write({"active": False})

    def _confirmed_order_with_partial_delivery(self, ordered_qty, delivered_qty):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": ordered_qty, "price_unit": 100.0})
                ],
            }
        )
        order.action_confirm()
        picking = order.picking_ids[:1]
        picking.move_ids.quantity = delivered_qty
        picking.move_ids.picked = True
        picking.with_context(skip_backorder=True)._action_done()
        return order

    def test_cancel_remaining_records_lost_qty_with_reason(self):
        """20 ordered, 12 delivered: cancelling remainders leaves 8 as unsold."""
        order = self._confirmed_order_with_partial_delivery(20.0, 12.0)
        line = order.order_line
        self.assertEqual(line.qty_delivered, 12.0)

        line.with_context(cancel_from_order=True, cancel_lost_reason_id=self.lost_reason.id).button_cancel_remaining()

        self.assertEqual(line.product_uom_qty, 12.0)
        self.assertEqual(line.lost_qty, 8.0)
        self.assertEqual(line.lost_reason_id, self.lost_reason)
        self.assertTrue(line.is_sold, "a confirmed and partly delivered line stays sold")

    def test_cancel_remaining_without_reason_leaves_no_lost_qty(self):
        """With the setting off nothing changes: no reason, no unsold quantity."""
        order = self._confirmed_order_with_partial_delivery(20.0, 12.0)
        line = order.order_line

        line.with_context(cancel_from_order=True).button_cancel_remaining()

        self.assertEqual(line.product_uom_qty, 12.0)
        self.assertEqual(line.lost_qty, 0.0)
        self.assertFalse(line.lost_reason_id)

    def test_cancel_remaining_twice_does_not_add_up(self):
        """Running it again cancels nothing, so the unsold quantity does not grow."""
        order = self._confirmed_order_with_partial_delivery(20.0, 12.0)
        line = order.order_line
        ctx = {"cancel_from_order": True, "cancel_lost_reason_id": self.lost_reason.id}

        line.with_context(**ctx).button_cancel_remaining()
        line.with_context(**ctx).button_cancel_remaining()

        self.assertEqual(line.lost_qty, 8.0)

    def test_wizard_asks_for_the_reason(self):
        """The wizard records the reason on every line it cancels."""
        order = self._confirmed_order_with_partial_delivery(20.0, 12.0)
        wizard = (
            self.env["sale.order.cancel.remaining"]
            .with_context(active_ids=order.ids)
            .create({"lost_reason_id": self.lost_reason.id})
        )
        self.assertEqual(wizard.sale_order_line_ids, order.order_line)

        wizard.action_confirm()

        self.assertEqual(order.order_line.lost_qty, 8.0)
        self.assertEqual(order.order_line.lost_reason_id, self.lost_reason)

    def test_line_button_opens_the_wizard_on_that_line_only(self):
        """The line button opens the wizard restricted to its own line."""
        order = self._confirmed_order_with_partial_delivery(20.0, 12.0)
        action = order.order_line.action_open_cancel_remaining()
        self.assertEqual(action["res_model"], "sale.order.cancel.remaining")
        self.assertEqual(action["context"]["default_sale_order_line_ids"], [(6, 0, order.order_line.ids)])

        wizard = (
            self.env["sale.order.cancel.remaining"]
            .with_context(**action["context"])
            .create({"lost_reason_id": self.lost_reason.id})
        )
        self.assertEqual(wizard.sale_order_line_ids, order.order_line)

    def test_cancel_remaining_requires_a_valid_reason(self):
        """An unsold quantity without a reason is still rejected by the constraint."""
        order = self._confirmed_order_with_partial_delivery(20.0, 12.0)
        with self.assertRaises(ValidationError):
            order.order_line.write({"lost_qty": 8.0})
