##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from unittest.mock import patch

from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestInvoiceAutomationError(TestSaleCommon):
    @classmethod
    def setup_independent_user(cls):
        # Keep superuser context for setup in deployments with stricter product ACLs.
        return None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.validate_invoice_type = cls.env["sale.order.type"].create(
            {
                "name": "Test Validate Invoice Automation",
                "company_id": cls.env.company.id,
                "invoicing_atomation": "validate_invoice",
                "journal_id": cls.company_data["default_journal_sale"].id,
            }
        )
        sale_exception_installed = cls.env["sale.order"]._fields.get("ignore_exception")
        if sale_exception_installed:
            cls.env["exception.rule"].search([("active", "=", True)]).write({"active": False})

    def _create_so(self):
        product = self.company_data["product_service_order"]
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "type_id": self.validate_invoice_type.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": 1.0,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )

    def test_arca_timeout_keeps_invoice_and_logs_error(self):
        """Al fallar action_post (ej. timeout ARCA), la factura queda en draft y
        se registra el error en el chatter de la factura y de la orden de venta."""
        so = self._create_so()
        AccountMove = self.env["account.move"]
        with patch.object(
            type(AccountMove),
            "action_post",
            side_effect=Exception("ARCA timeout"),
        ):
            so.action_confirm()

        self.assertEqual(len(so.invoice_ids), 1, "La factura debe haberse creado")
        invoice = so.invoice_ids
        self.assertTrue(invoice.exists(), "La factura no debe haberse borrado por el savepoint")
        self.assertEqual(invoice.state, "draft", "La factura debe quedar en draft si action_post falla")
        self.assertTrue(
            any("ARCA timeout" in (m.body or "") for m in invoice.message_ids),
            "Se esperaba mensaje de error en el chatter de la factura",
        )
        self.assertTrue(
            any("ARCA timeout" in (m.body or "") for m in so.message_ids),
            "Se esperaba mensaje de error en el chatter de la orden de venta",
        )
