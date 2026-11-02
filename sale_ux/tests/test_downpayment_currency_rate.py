##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestDownpaymentCurrencyRate(AccountTestInvoicingCommon):
    """Down payment in a foreign currency invoiced at one rate and deducted at another."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "exception.rule" in cls.env:
            cls.env["exception.rule"].sudo().search([]).write({"active": False})
        cls.foreign_currency = cls.setup_other_currency(
            "EUR", rates=[("2016-01-01", 0.000625), ("2016-06-01", 0.00065)]
        )
        cls.product = cls._create_product(
            name="DP currency product", type="consu", invoice_policy="order", taxes_id=False
        )

    def _create_order(self, currency):
        pricelist = self.env["product.pricelist"].create({"name": "DP pricelist", "currency_id": currency.id})
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "pricelist_id": pricelist.id,
                "order_line": [
                    Command.create({"product_id": self.product.id, "product_uom_qty": 4.0, "price_unit": 1000.0}),
                ],
            }
        )
        order.action_confirm()
        return order

    def _invoice_downpayment(self, order, invoice_date):
        self.env["sale.advance.payment.inv"].with_context(
            active_model="sale.order", active_ids=order.ids, active_id=order.id
        ).create({"advance_payment_method": "percentage", "amount": 25}).create_invoices()
        downpayment = order.invoice_ids
        downpayment.invoice_date = invoice_date
        downpayment.action_post()
        return downpayment

    def _deduct_downpayment(self, order, invoice_date):
        """Invoice part of the order deducting the down payment, as the client did."""
        invoice = order._create_invoices(final=True)
        invoice.invoice_line_ids.filtered(lambda line: not line.is_downpayment).quantity = 3.0
        invoice.invoice_date = invoice_date
        invoice.action_post()
        return invoice

    def test_downpayment_deducted_at_another_rate(self):
        """The rate changed between both invoices: the down payment is still deducted."""
        order = self._create_order(self.foreign_currency)
        self._invoice_downpayment(order, "2016-01-15")
        self._deduct_downpayment(order, "2016-06-15")
        dp_line = order.order_line.filtered(lambda line: line.is_downpayment and not line.display_type)

        self.assertNotEqual(sum(dp_line.invoice_lines.mapped("balance")), 0.0, "the scenario needs a different rate")
        self.assertEqual(dp_line.qty_invoiced, 0.0)
        self.assertEqual(dp_line.qty_to_invoice, 0.0)

        final_invoice = order._create_invoices(final=True)
        self.assertEqual(final_invoice.move_type, "out_invoice", "the balance must not come out as a refund")
        self.assertFalse(final_invoice.invoice_line_ids.filtered("is_downpayment"))
        self.assertAlmostEqual(final_invoice.amount_untaxed, 1000.0, places=2)

    def test_downpayment_not_deducted_yet(self):
        """A foreign currency down payment still pending is deducted in the next invoice."""
        order = self._create_order(self.foreign_currency)
        self._invoice_downpayment(order, "2016-01-15")
        dp_line = order.order_line.filtered(lambda line: line.is_downpayment and not line.display_type)

        self.assertEqual(dp_line.qty_invoiced, 1.0)
        self.assertEqual(dp_line.qty_to_invoice, -1.0)

        final_invoice = order._create_invoices(final=True)
        self.assertTrue(final_invoice.invoice_line_ids.filtered("is_downpayment"))
        self.assertAlmostEqual(final_invoice.amount_untaxed, 3000.0, places=2)

    def test_downpayment_in_company_currency(self):
        """In the company currency the behavior does not change."""
        order = self._create_order(self.env.company.currency_id)
        self._invoice_downpayment(order, "2016-01-15")
        dp_line = order.order_line.filtered(lambda line: line.is_downpayment and not line.display_type)
        self.assertEqual(dp_line.qty_invoiced, 1.0)

        self._deduct_downpayment(order, "2016-06-15")
        self.assertEqual(dp_line.qty_invoiced, 0.0)
        self.assertEqual(dp_line.qty_to_invoice, 0.0)
