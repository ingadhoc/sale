##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleOrderTypeAutomation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env.ref("base.res_partner_1")
        cls.sale_type = cls.env.ref("sale_order_type.normal_sale_type")
        cls.sale_type.company_id = cls.env.company
        cls.invoice_journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Sale Order Type Automation Product",
                "type": "consu",
                "invoice_policy": "order",
                "list_price": 100.0,
            }
        )
        cls.payment_journal = cls.env["account.journal"].search(
            [
                ("type", "in", ["cash", "bank"]),
                ("inbound_payment_method_line_ids.code", "=", "manual"),
                ("company_id", "=", cls.sale_type.invoice_company_id.id),
            ],
            limit=1,
        )

    def _create_order(self, **extra_vals):
        vals = {
            "partner_id": self.partner.id,
            "type_id": self.sale_type.id,
            "order_line": [
                Command.create(
                    {
                        "product_id": self.product.id,
                        "product_uom_qty": 1.0,
                        "price_unit": 100.0,
                    }
                )
            ],
        }
        vals.update(extra_vals)
        return self.env["sale.order"].with_context(ignore_exception=True).create(vals)

    def test_action_confirm_creates_invoice_when_configured(self):
        self.sale_type.write(
            {
                "invoicing_atomation": "create_invoice",
                "journal_id": self.invoice_journal.id,
                "picking_atomation": "none",
                "set_done_on_confirmation": False,
                "invoice_validate_domain": False,
            }
        )
        order = self._create_order()

        order.with_context(ignore_exception=True).action_confirm()

        self.assertTrue(order.invoice_ids)
        self.assertEqual(set(order.invoice_ids.mapped("state")), {"draft"})

    def test_action_confirm_posts_invoice_when_validate_mode(self):
        self.sale_type.write(
            {
                "invoicing_atomation": "validate_invoice",
                "journal_id": self.invoice_journal.id,
                "picking_atomation": "none",
                "invoice_validate_domain": False,
            }
        )
        order = self._create_order()

        order.with_context(ignore_exception=True).action_confirm()

        self.assertTrue(order.invoice_ids)
        self.assertEqual(set(order.invoice_ids.mapped("state")), {"posted"})

    def test_action_confirm_sets_order_done_when_configured(self):
        self.sale_type.write(
            {
                "invoicing_atomation": "none",
                "picking_atomation": "none",
                "set_done_on_confirmation": True,
            }
        )
        order = self._create_order()

        order.with_context(ignore_exception=True).action_confirm()

        self.assertEqual(order.state, "sale")
        self.assertTrue(order.locked)

    def test_validate_payment_automation_requires_payment_journal(self):
        with self.assertRaises(ValidationError):
            self.sale_type.write(
                {
                    "payment_atomation": "validate_payment",
                    "payment_journal_id": False,
                }
            )

    def test_validate_payment_automation_accepts_valid_payment_journal(self):
        if not self.payment_journal:
            self.skipTest("No manual payment journal available for current company")

        self.sale_type.write(
            {
                "payment_journal_id": self.payment_journal.id,
                "payment_atomation": "validate_payment",
            }
        )

        self.assertEqual(self.sale_type.payment_atomation, "validate_payment")
        self.assertEqual(self.sale_type.payment_journal_id, self.payment_journal)
