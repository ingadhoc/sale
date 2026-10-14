from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import SaleUxCommon


@tagged("post_install", "-at_install")
class TestSaleUxWizards(SaleUxCommon):
    def test_advance_payment_amount_total_computes_taxes(self):
        order = self._create_sale_order()
        tax = self.env["account.tax"].create(
            {
                "name": "Sale UX 21%",
                "amount_type": "percent",
                "amount": 21,
                "type_tax_use": "sale",
            }
        )
        wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(active_ids=order.ids)
            .create(
                {
                    "advance_payment_method": "fixed",
                    "amount": 100.0,
                    "tax_ids": [Command.set(tax.ids)],
                }
            )
        )

        wizard._compute_amount_total()

        self.assertAlmostEqual(wizard.amount_total, 121.0)

    def test_advance_payment_inverse_amount_total_removes_percent_taxes(self):
        order = self._create_sale_order()
        tax = self.env["account.tax"].create(
            {
                "name": "Sale UX 10%",
                "amount_type": "percent",
                "amount": 10,
                "type_tax_use": "sale",
            }
        )
        wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(active_ids=order.ids)
            .create(
                {
                    "advance_payment_method": "fixed",
                    "amount_total": 110.0,
                    "tax_ids": [Command.set(tax.ids)],
                }
            )
        )

        wizard._inverse_amount_total()

        self.assertAlmostEqual(wizard.amount, 100.0)

    def test_advance_payment_inverse_amount_total_rejects_non_percent_taxes(self):
        order = self._create_sale_order()
        tax = self.env["account.tax"].create(
            {
                "name": "Sale UX fixed tax",
                "amount_type": "fixed",
                "amount": 5,
                "type_tax_use": "sale",
            }
        )
        wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(active_ids=order.ids)
            .create(
                {
                    "advance_payment_method": "fixed",
                    "amount": 100.0,
                    "tax_ids": [Command.set(tax.ids)],
                }
            )
        )

        with self.assertRaises(ValidationError):
            wizard.amount_total = 105.0
            wizard._inverse_amount_total()
