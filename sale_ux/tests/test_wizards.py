from odoo import Command
from odoo.tests import tagged

from .common import SaleUxCommon


@tagged("post_install", "-at_install")
class TestSaleUxWizards(SaleUxCommon):
    """In 20 the fixed amount of a down payment is already the total with taxes, so sale_ux no longer
    carries its own "amount with taxes" field. These tests pin the native behaviour it relies on."""

    def _advance_payment_wizard(self, order, **values):
        return (
            self.env["sale.advance.payment.inv"]
            .with_context(active_ids=order.ids, active_model="sale.order")
            .create({"advance_payment_method": "fixed", **values})
        )

    def _order_with_taxes(self, *taxes):
        order = self._create_sale_order(
            order_line=[
                Command.create(
                    {
                        "product_id": self.product.id,
                        "product_uom_qty": 2.0,
                        "price_unit": 100.0,
                        "tax_ids": [Command.set(tax.ids)],
                    }
                )
                for tax in taxes
            ]
        )
        order.action_confirm()
        return order

    def test_fixed_down_payment_is_the_total_with_taxes(self):
        order = self._order_with_taxes(self.tax_sale_a)  # 10% on 200 -> order total 220

        self._advance_payment_wizard(order, fixed_amount=110.0).create_invoices()

        invoice = order.invoice_ids
        self.assertAlmostEqual(invoice.amount_total, 110.0)
        self.assertAlmostEqual(invoice.amount_untaxed, 100.0)
        self.assertAlmostEqual(invoice.amount_tax, 10.0)

    def test_fixed_down_payment_with_different_taxes_invoices_the_amount_asked(self):
        tax_21 = self.env["account.tax"].create(
            {"name": "Sale UX 21%", "amount_type": "percent", "amount": 21.0, "type_tax_use": "sale"}
        )
        order = self._order_with_taxes(self.tax_sale_a, tax_21)

        self._advance_payment_wizard(order, fixed_amount=100.0).create_invoices()

        invoice = order.invoice_ids
        self.assertAlmostEqual(invoice.amount_total, 100.0)
        self.assertEqual(len(invoice.invoice_line_ids), 2, "one down payment line per tax")

    def test_down_payment_wizard_has_only_the_native_amount_fields(self):
        arch = self.env["sale.advance.payment.inv"].get_view(view_type="form")["arch"]

        self.assertIn('name="fixed_amount"', arch)
        self.assertNotIn('name="amount_total"', arch)
        self.assertNotIn("amount_total", self.env["sale.advance.payment.inv"]._fields)
        self.assertNotIn("tax_ids", self.env["sale.advance.payment.inv"]._fields)
