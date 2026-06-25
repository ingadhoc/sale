##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestSaleOrderUnlink(TestSaleCommon):
    @classmethod
    def setup_independent_user(cls):
        return None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "SO Unlink Test Service",
                "type": "service",
                "invoice_policy": "order",
                "list_price": 100.0,
            }
        )

    def _create_sale_order(self):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )

    def _create_linked_invoice(self, sale_order):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": sale_order.partner_id.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "SO unlink traceability test",
                            "product_id": self.product.id,
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "sale_line_ids": [(6, 0, sale_order.order_line.ids)],
                        },
                    )
                ],
            }
        )

    def test_unlink_blocked_if_has_invoices(self):
        sale_order = self._create_sale_order()
        sale_order.action_confirm()
        self._create_linked_invoice(sale_order)
        sale_order.action_cancel()

        with self.assertRaisesRegex(
            UserError,
            "You cannot delete this sales order because it has related invoices",
        ):
            sale_order.unlink()

    def test_unlink_allowed_if_no_invoices(self):
        sale_order = self._create_sale_order()
        sale_order.action_cancel()
        sale_order.unlink()

        self.assertFalse(sale_order.exists())

    def _create_downpayment_invoice(self, sale_order, amount=50.0):
        wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(active_model="sale.order", active_ids=sale_order.ids, active_id=sale_order.id)
            .create({"advance_payment_method": "fixed", "fixed_amount": amount})
        )
        wizard.create_invoices()
        return sale_order.invoice_ids.filtered(lambda move: move.state == "draft")[-1:]

    def test_reset_to_draft_removes_cancelled_downpayment(self):
        sale_order = self._create_sale_order()
        sale_order.action_confirm()
        invoice = self._create_downpayment_invoice(sale_order)
        downpayment_line = sale_order.order_line.filtered(lambda line: line.is_downpayment and not line.display_type)
        self.assertTrue(downpayment_line)

        invoice.button_cancel()
        self.assertEqual(downpayment_line._get_downpayment_state(), "cancel")

        order_messages_before = len(sale_order.message_ids)
        invoice_messages_before = len(invoice.message_ids)

        sale_order.action_cancel()
        sale_order.action_draft()

        self.assertFalse(downpayment_line.exists())
        self.assertGreater(len(sale_order.message_ids), order_messages_before)
        self.assertTrue(sale_order.message_ids.filtered(lambda m: m.body and "removed on reset to draft" in m.body))
        self.assertGreater(len(invoice.message_ids), invoice_messages_before)
        self.assertTrue(invoice.message_ids.filtered(lambda m: m.body and "removed" in m.body))

    def test_reset_to_draft_only_targets_cancelled_downpayments(self):
        sale_order = self._create_sale_order()
        sale_order.action_confirm()
        self._create_downpayment_invoice(sale_order)
        downpayment_line = sale_order.order_line.filtered(lambda line: line.is_downpayment and not line.display_type)
        self.assertTrue(downpayment_line)
        self.assertEqual(downpayment_line._get_downpayment_state(), "draft")

        sale_order.action_cancel()
        self.assertEqual(downpayment_line._get_downpayment_state(), "cancel")
        sale_order.action_draft()
        self.assertFalse(downpayment_line.exists())

    def test_reset_to_draft_without_downpayment_posts_no_log(self):
        sale_order = self._create_sale_order()
        sale_order.action_confirm()
        sale_order.action_cancel()
        messages_before = len(sale_order.message_ids)
        sale_order.action_draft()
        self.assertFalse(sale_order.message_ids.filtered(lambda m: m.body and "down payment" in m.body.lower()))
        self.assertEqual(len(sale_order.message_ids), messages_before)
