##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestSaleOrderTypeAutomation(TestSaleCommon):
    @classmethod
    def setup_independent_user(cls):
        return None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.partner_a
        cls.invoice_journal = cls.company_data["default_journal_sale"]
        cls.sale_type = cls.env["sale.order.type"].create(
            {
                "name": "Test Sale Order Type Automation",
                "company_id": cls.env.company.id,
                "journal_id": cls.invoice_journal.id,
            }
        )
        if cls.env["sale.order"]._fields.get("ignore_exception"):
            cls.env["exception.rule"].search([("active", "=", True)]).write({"active": False})
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
                ("outbound_payment_method_line_ids.code", "=", "manual"),
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
        return self.env["sale.order"].create(vals)

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

        order.action_confirm()

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

        order.action_confirm()

        self.assertEqual(order.state, "sale")
        invoice = order.invoice_ids
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, "posted")
        self.assertNotIn(invoice.name, (False, "/"), "a posted invoice has to be numbered")
        if "l10n_latam_document_type_id" in invoice._fields and invoice.l10n_latam_use_documents:
            self.assertTrue(invoice.l10n_latam_document_type_id, "a posted invoice needs its document type")

    def test_action_confirm_sets_order_done_when_configured(self):
        self.sale_type.write(
            {
                "invoicing_atomation": "none",
                "picking_atomation": "none",
                "set_done_on_confirmation": True,
            }
        )
        order = self._create_order()

        order.action_confirm()

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

    def test_prepare_payment_uses_invoice_company(self):
        # regression: the payment must be built on the invoice company. On a branch that
        # invoices while the payment journal belongs to the parent, leaving the payment on
        # the journal's company raised a cross-company error (parent_of consistency check).
        self.sale_type.write(
            {
                "invoicing_atomation": "validate_invoice",
                "journal_id": self.invoice_journal.id,
                "picking_atomation": "none",
                "invoice_validate_domain": False,
            }
        )
        order = self._create_order()
        order.action_confirm()
        invoice = order.invoice_ids

        vals = invoice._prepare_dict_account_payment(invoice, self.invoice_journal)

        self.assertEqual(vals["company_id"], invoice.company_id.id)

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
