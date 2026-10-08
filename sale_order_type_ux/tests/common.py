##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.tests.common import TransactionCase


class SaleOrderTypeUxCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context={
                **cls.env.context,
                "mail_create_nolog": True,
                "mail_create_nosubscribe": True,
                "tracking_disable": True,
            }
        )
        suffix = str(sum(ord(char) for char in cls.__name__))
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": f"SOT UX Other Company {suffix}"})

        cls.receivable_account = cls.env["account.account"].create(
            {
                "name": "SOT UX Receivable",
                "code": f"TREC{suffix}",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        cls.income_account = cls.env["account.account"].create(
            {"name": "SOT UX Income", "code": f"TINC{suffix}", "account_type": "income"}
        )
        cls.sale_journal = cls.env["account.journal"].create(
            {
                "name": f"SOT UX Sale Journal {suffix}",
                "type": "sale",
                "code": f"TSJ{suffix[:3]}",
                "company_id": cls.company.id,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "SOT UX Customer",
                "property_account_receivable_id": cls.receivable_account.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "SOT UX Product",
                "type": "consu",
                "invoice_policy": "order",
                "list_price": 100.0,
                "property_account_income_id": cls.income_account.id,
                "taxes_id": [Command.clear()],
            }
        )
        cls.fiscal_position = cls.env["account.fiscal.position"].create(
            {"name": f"SOT UX Fiscal Position {suffix}", "company_id": cls.company.id}
        )
        cls.sales_team = cls.env["crm.team"].create({"name": f"SOT UX Team {suffix}"})

        SaleOrderType = cls.env["sale.order.type"]
        cls.type_a = SaleOrderType.create({"name": f"SOT UX Type A {suffix}"})
        cls.type_b = SaleOrderType.create({"name": f"SOT UX Type B {suffix}"})

    @classmethod
    def _create_order(cls, order_type, **values):
        order_values = {
            "partner_id": cls.partner.id,
            "type_id": order_type.id,
            "order_line": [
                Command.create(
                    {
                        "product_id": cls.product.id,
                        "product_uom_qty": 1.0,
                        "price_unit": 100.0,
                        "tax_ids": [Command.clear()],
                    }
                )
            ],
        }
        order_values.update(values)
        return cls.env["sale.order"].create(order_values)

    def assert_invoices_keep_their_type(self, orders, invoices):
        """Invariant: every invoice carries the type of the orders it came from.

        Runs after any invoicing operation of the suite. It is the check that
        catches the type getting lost on the way to the invoice while the
        amounts still look right.
        """
        self.assertTrue(invoices, "invoicing produced no invoice at all")
        for invoice in invoices:
            source_orders = orders.filtered(lambda o, i=invoice: i in o.invoice_ids)
            self.assertTrue(
                source_orders,
                f"invoice {invoice.name} does not belong to any of the orders under test",
            )
            self.assertEqual(
                invoice.sale_type_id,
                source_orders.type_id,
                "the invoice does not carry the sale order type of its orders",
            )
            self.assertNotEqual(len(invoice.invoice_line_ids), 0, "the invoice has no lines")
