##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import contextlib
from unittest.mock import patch

from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.exceptions import UserError, ValidationError
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

    BLOCKING_REASON = "Falta la Responsabilidad ARCA"

    @contextlib.contextmanager
    def _blocked_invoices(self):
        """Fuerza un motivo de bloqueo y falla ruidosamente si igual se intenta registrar."""
        AccountMove = type(self.env["account.move"])
        with (
            patch.object(
                AccountMove,
                "_get_invoicing_automation_blocking_reasons",
                lambda moves: dict.fromkeys(moves.ids, self.BLOCKING_REASON),
            ),
            patch.object(
                AccountMove,
                "action_post",
                side_effect=AssertionError("no se debe intentar registrar la factura"),
            ),
        ):
            yield

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

    def test_blocking_reason_aborts_confirmation(self):
        """Si ya se sabe que la factura no se puede registrar, la confirmación de la venta
        se traba (como en la v18) y no se intenta registrar nada."""
        so = self._create_so()
        with self._blocked_invoices():
            with self.assertRaises(UserError) as capture:
                so.action_confirm()

        self.assertIn(self.BLOCKING_REASON, str(capture.exception))
        # En uso real el UserError revierte la confirmación por el rollback del request; acá
        # sólo podemos verificar que ninguna factura llegó a registrarse.
        self.assertFalse(
            so.invoice_ids.filtered(lambda x: x.state == "posted"),
            "No debe haber quedado ninguna factura registrada",
        )

    def test_blocking_reason_does_not_abort_batch(self):
        """En el camino batch (ya commiteado) no se puede trabar: la factura queda como
        borrador limpio con el motivo en el chatter."""
        so = self._create_so()
        # el módulo hace cr.commit() en este camino y los tests de Odoo lo prohíben
        with self._blocked_invoices(), patch.object(self.env.cr, "commit", lambda: None):
            so.with_context(commit_invoice_automation=True).action_confirm()

        invoice = so.invoice_ids
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, "draft", "La factura debe quedar en borrador")
        self.assertTrue(
            any(self.BLOCKING_REASON in (m.body or "") for m in invoice.message_ids),
            "Se esperaba el motivo en el chatter de la factura",
        )
        self.assertTrue(
            any(self.BLOCKING_REASON in (m.body or "") for m in so.message_ids),
            "Se esperaba el motivo en el chatter del pedido de venta",
        )

    def test_failed_post_does_not_leave_invoice_posted(self):
        """Reproduce el bug del ticket 125388: action_post escribe state='posted' y recién
        entonces falla la constraint. Sin revertir, el flush del propio aviso de error
        persiste una factura registrada sin número ni tipo de documento."""
        so = self._create_so()
        AccountMove = self.env["account.move"]

        def _post_then_fail(moves):
            # mismo orden que account.move._post: primero el write, después la validación.
            # Sin tipo de documento la localización no puede numerar, así que el name queda
            # en "/" — es la forma exacta de los registros corruptos que dejó el bug.
            moves.write({"state": "posted", "posted_before": True, "name": "/"})
            raise ValidationError("El diario requiere un tipo de documento")

        with patch.object(type(AccountMove), "action_post", _post_then_fail):
            so.action_confirm()

        invoice = so.invoice_ids
        self.assertEqual(len(invoice), 1)
        self.assertEqual(
            invoice.state,
            "draft",
            "La factura no debe quedar registrada cuando falló la validación automática",
        )
        self.assertFalse(invoice.posted_before)
        self.assertIn(invoice.name, (False, "/"), "La factura no debe haber quedado numerada")
        self.assertTrue(
            any("tipo de documento" in (m.body or "") for m in so.message_ids),
            "Se esperaba el aviso del error en el chatter del pedido de venta",
        )
