from odoo import Command, fields
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT
from odoo.tests.common import TransactionCase

from .invariants import SaleUxInvariants


class SaleUxCommon(SaleUxInvariants, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context={
                **cls.env.context,
                **DISABLED_MAIL_CONTEXT,
                "tracking_disable": True,
            }
        )
        cls.IrConfig = cls.env["ir.config_parameter"].sudo()
        cls.product_uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.product_uom_pack = cls.env.ref("uom.product_uom_dozen")
        code_suffix = str(sum(ord(char) for char in cls.__name__))

        cls.receivable_account = cls.env["account.account"].create(
            {
                "name": "Sale UX Test Receivable",
                "code": f"TREC{code_suffix}",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        cls.payable_account = cls.env["account.account"].create(
            {
                "name": "Sale UX Test Payable",
                "code": f"TPAY{code_suffix}",
                "account_type": "liability_payable",
                "reconcile": True,
            }
        )
        cls.income_account = cls.env["account.account"].create(
            {
                "name": "Sale UX Test Income",
                "code": f"TINC{code_suffix}",
                "account_type": "income",
            }
        )
        cls.expense_account = cls.env["account.account"].create(
            {
                "name": "Sale UX Test Expense",
                "code": f"TEXP{code_suffix}",
                "account_type": "expense",
            }
        )
        cls.partner_a = cls.env["res.partner"].create(
            {
                "name": "Sale UX Customer A",
                "property_account_receivable_id": cls.receivable_account.id,
                "property_account_payable_id": cls.payable_account.id,
            }
        )
        cls.partner_b = cls.env["res.partner"].create(
            {
                "name": "Sale UX Customer B",
                "property_account_receivable_id": cls.receivable_account.id,
                "property_account_payable_id": cls.payable_account.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Sale UX Product",
                "type": "consu",
                "invoice_policy": "order",
                "list_price": 100.0,
                "standard_price": 50.0,
                "uom_id": cls.product_uom_unit.id,
                "property_account_income_id": cls.income_account.id,
                "property_account_expense_id": cls.expense_account.id,
                "taxes_id": [Command.clear()],
                "supplier_taxes_id": [Command.clear()],
            }
        )
        cls.tax_sale_a = cls.env["account.tax"].create(
            {
                "name": "Sale UX Tax",
                "amount_type": "percent",
                "amount": 10.0,
                "type_tax_use": "sale",
            }
        )

    @classmethod
    def _create_sale_order(cls, **values):
        order_values = {
            "partner_id": cls.partner_a.id,
            "order_line": [
                Command.create(
                    {
                        "product_id": cls.product.id,
                        "product_uom_qty": 2.0,
                        "price_unit": 100.0,
                        "tax_ids": [Command.clear()],
                    }
                )
            ],
        }
        order_values.update(values)
        return cls.env["sale.order"].create(order_values)

    @classmethod
    def _create_old_quotation(cls, days_old):
        return cls._create_sale_order(
            date_order=fields.Datetime.subtract(fields.Datetime.now(), days=days_old),
        )
