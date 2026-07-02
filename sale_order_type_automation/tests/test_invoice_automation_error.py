##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from unittest.mock import MagicMock, patch

import psycopg2
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

    def test_db_error_on_action_post_does_not_break_confirmation(self):
        """Un error a nivel DB al validar la factura deja la transacción abortada;
        el aviso de fallo no debe filtrar InFailedSqlTransaction ni tumbar la
        confirmación: el cursor se recupera y el mensaje se re-postea en la
        factura y la orden (tickets #121857 / #121927; comportamiento de 67846).

        La caída real (savepoint destruido por el commit del CAE + error DB) no se
        puede reproducir íntegra en un TransactionCase: el framework prohíbe el
        rollback real y, sin commit, cualquier recuperación borraría los registros
        del test. Simulamos el síntoma exacto: action_post revienta (se entra al
        except) y el primer message_post falla con InFailedSqlTransaction, que es
        donde el bug tumbaba todo."""
        so = self._create_so()
        AccountMove = self.env["account.move"]
        Move = type(AccountMove)
        orig_action_post = Move.action_post
        orig_message_post = Move.message_post

        def _failing_action_post(records, *args, **kwargs):
            # Crea/postea la factura de verdad y luego falla la validación: el
            # savepoint revierte el posteo (factura queda en draft) y se entra al
            # except de run_invoicing_atomation, igual que en producción.
            orig_action_post(records, *args, **kwargs)
            raise Exception("automatic invoice validation failed")

        state = {"aborted": False}

        def _message_post_aborted_once(records, *args, **kwargs):
            body = kwargs.get("body") or (args[0] if args else "")
            if "couldn't validate" in (body or "") and not state["aborted"]:
                # Primer intento de dejar el aviso: la tx está abortada.
                state["aborted"] = True
                raise psycopg2.errors.InFailedSqlTransaction("current transaction is aborted, commands ignored")
            return orig_message_post(records, *args, **kwargs)

        rollback_mock = MagicMock()
        logger = "odoo.addons.sale_order_type_automation.models.sale_order"
        with patch.object(Move, "action_post", _failing_action_post), patch.object(
            Move, "message_post", _message_post_aborted_once
        ), patch.object(so.env.cr, "rollback", rollback_mock), self.assertLogs(logger, level="WARNING") as log_catcher:
            try:
                so.action_confirm()
            except psycopg2.Error as error:
                self.fail("action_confirm() leaked a database error instead of " "handling it gracefully: %r" % error)

        # Se intentó postear el aviso, falló por tx abortada y el fix lo detectó.
        self.assertTrue(state["aborted"], "The first message_post should have failed")
        # El fix recuperó la transacción en lugar de tumbar la confirmación.
        self.assertTrue(
            rollback_mock.called,
            "The aborted transaction should have been rolled back",
        )
        self.assertTrue(
            any("aborted, recovering" in line for line in log_catcher.output),
            "The aborted-transaction recovery should be logged, got: %s" % log_catcher.output,
        )
        # Tras recuperar, el aviso quedó en el chatter de la factura y de la orden.
        self.assertTrue(
            any("couldn't validate" in (m.body or "").lower() for m in so.message_ids),
            "The validation failure should be logged on the sale order chatter",
        )
        self.assertTrue(
            so.invoice_ids and any("couldn't validate" in (m.body or "").lower() for m in so.invoice_ids.message_ids),
            "The validation failure should be logged on the invoice chatter",
        )
