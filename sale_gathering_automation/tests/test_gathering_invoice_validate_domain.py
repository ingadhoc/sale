##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import odoo.tests.common as common


class TestGatheringInvoiceValidateDomain(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create({"name": "Test Gathering Partner"})
        self.product = self.env.ref("product.product_product_4")
        invoice_journal = self.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        self.gathering_validate_type = self.env["sale.order.type"].create(
            {
                "name": "Test Gathering Validate Invoice Domain",
                "company_id": self.env.company.id,
                "invoicing_atomation": "validate_invoice",
                "journal_id": invoice_journal.id,
                "invoice_validate_domain": "[('move_type', '=', 'out_invoice')]",
            }
        )
        sale_exception_installed = self.env["sale.order"]._fields.get("ignore_exception")
        if sale_exception_installed:
            self.env["exception.rule"].search([("active", "=", True)]).write({"active": False})
        if "loyalty.program" in self.env:
            self.env["loyalty.program"].search([("active", "=", True)]).write({"active": False})

    def test_invoice_validate_domain_match_stays_draft(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "type_id": self.gathering_validate_type.id,
                "is_gathering": True,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 5.0,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )
        order.action_confirm()

        self.assertTrue(
            order.invoice_ids,
            "Gathering invoice must be created on confirmation",
        )
        for invoice in order.invoice_ids:
            self.assertEqual(
                invoice.state,
                "draft",
                "Invoice %s (move_type=%r) must stay in draft because it matches "
                "invoice_validate_domain (match -> stays draft), but state is '%s'"
                % (invoice.id, invoice.move_type, invoice.state),
            )
