##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestDownpaymentDiscount(AccountTestInvoicingCommon):
    """Down payment invoiced with a discount on its line and deducted later."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "exception.rule" in cls.env:
            cls.env["exception.rule"].sudo().search([]).write({"active": False})
        cls.product = cls._create_product(
            name="DP discount product", type="consu", invoice_policy="order", taxes_id=False
        )

    def _create_order(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "order_line": [
                    Command.create({"product_id": self.product.id, "product_uom_qty": 1.0, "price_unit": 900.0}),
                    Command.create({"product_id": self.product.id, "product_uom_qty": 1.0, "price_unit": 3100.0}),
                ],
            }
        )
        order.action_confirm()
        return order

    def _invoice_downpayment(self, order, discount):
        """Invoice a 1000 down payment and discount its line before posting, as the client did."""
        self.env["sale.advance.payment.inv"].with_context(
            active_model="sale.order", active_ids=order.ids, active_id=order.id
        ).create({"advance_payment_method": "fixed", "fixed_amount": 1000.0}).create_invoices()
        downpayment = order.invoice_ids.filtered(lambda move: move.state == "draft")
        downpayment.invoice_line_ids.filtered("is_downpayment").discount = discount
        downpayment.action_post()
        return downpayment

    def _downpayment_order_line(self, order):
        return order.order_line.filtered(lambda line: line.is_downpayment and not line.display_type)

    def test_discounted_downpayment_deducts_the_charged_amount(self):
        """The order line takes the net of the down payment, not its gross price."""
        order = self._create_order()
        downpayment = self._invoice_downpayment(order, 15.0)
        self.assertAlmostEqual(downpayment.amount_untaxed, 850.0, places=2)

        dp_line = self._downpayment_order_line(order)
        self.assertAlmostEqual(dp_line.price_unit, 850.0, places=2)

        final_invoice = order._create_invoices(final=True)
        self.assertAlmostEqual(final_invoice.amount_untaxed, 3150.0, places=2)

    def test_discounted_downpayment_partial_invoice_is_not_a_refund(self):
        """Invoicing only the smaller product must not turn the final invoice into a credit note."""
        order = self._create_order()
        self._invoice_downpayment(order, 15.0)

        final_invoice = order._create_invoices(final=True)
        product_lines = final_invoice.invoice_line_ids.filtered(lambda line: not line.is_downpayment)
        product_lines.filtered(lambda line: line.price_unit == 3100.0).unlink()
        final_invoice.action_post()

        self.assertEqual(final_invoice.move_type, "out_invoice", "the deduction must not flip the document type")
        self.assertAlmostEqual(final_invoice.amount_untaxed, 50.0, places=2)

    def test_downpayment_without_discount_is_unchanged(self):
        """Without a discount the standard amounts stay the same."""
        order = self._create_order()
        self._invoice_downpayment(order, 0.0)

        dp_line = self._downpayment_order_line(order)
        self.assertAlmostEqual(dp_line.price_unit, 1000.0, places=2)

        final_invoice = order._create_invoices(final=True)
        self.assertAlmostEqual(final_invoice.amount_untaxed, 3000.0, places=2)
