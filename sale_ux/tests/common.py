from odoo import Command, fields
from odoo.addons.base.tests.common import DISABLED_MAIL_CREATE_CONTEXT
from odoo.tests.common import TransactionCase


class SaleUxCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context={
                **cls.env.context,
                **DISABLED_MAIL_CREATE_CONTEXT,
                "tracking_disable": True,
                "mail_notrack": True,
            }
        )
        cls.IrConfig = cls.env["ir.config_parameter"].sudo()
        cls.product_uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.product_uom_pack = cls.env.ref("uom.product_uom_pack_6")
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


class ProductUomPriceCommon(TransactionCase):
    """A customer, a product sold by weight and two packagings of it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Its own company, so a localization installed in the base (taxes required per line,
        # for instance) does not decide whether these tests can create a line
        cls.company = cls.env["res.company"].create({"name": "Product UoM Price Co"})
        cls.env.user.company_ids = [Command.link(cls.company.id)]
        cls.env = cls.env(
            context={
                **cls.env.context,
                **DISABLED_MAIL_CREATE_CONTEXT,
                "tracking_disable": True,
                "allowed_company_ids": [cls.company.id],
            }
        )
        cls.env.user.company_id = cls.company
        cls.pricelist = cls.env["product.pricelist"].create(
            {"name": "Product UoM Price List", "company_id": cls.company.id}
        )
        cls.IrConfig = cls.env["ir.config_parameter"].sudo()
        cls.setting = "sale_ux.report_in_product_uom"

        cls.uom_kg = cls.env.ref("uom.product_uom_kgm")
        cls.uom_box_20 = cls.env["uom.uom"].create(
            {"name": "Box 20 kg", "relative_factor": 20.0, "relative_uom_id": cls.uom_kg.id}
        )
        cls.uom_box_15 = cls.env["uom.uom"].create(
            {"name": "Box 15 kg", "relative_factor": 15.0, "relative_uom_id": cls.uom_kg.id}
        )
        cls.product_kg = cls.env["product.product"].create(
            {
                "name": "Welding wire",
                "type": "consu",
                "list_price": 7.27,
                "uom_id": cls.uom_kg.id,
                "uom_ids": [Command.set([cls.uom_box_20.id, cls.uom_box_15.id])],
                "taxes_id": [Command.clear()],
            }
        )
        # An explicit language, activated here in case the base only has another one installed:
        # the report renders with the language of the customer, and without a known one the
        # decimal separator of the base decides whether a price reads 7.27 or 7,27
        cls.env["res.lang"]._activate_lang("en_US")
        cls.partner = cls.env["res.partner"].create({"name": "Product UoM Price Customer", "lang": "en_US"})

    @classmethod
    def _create_order(cls, uom, qty, price_unit, discount=0.0):
        return cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "company_id": cls.company.id,
                "pricelist_id": cls.pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.product_kg.id,
                            "product_uom_id": uom.id,
                            "product_uom_qty": qty,
                            "price_unit": price_unit,
                            "discount": discount,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
