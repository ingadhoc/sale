##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import unittest
from unittest.mock import patch

from odoo import Command
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.exceptions import RedirectWarning
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestBackgroundPostAutomation(TestSaleCommon):
    @classmethod
    def setup_independent_user(cls):
        return None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls.env["account.move"]._background_post_available():
            raise unittest.SkipTest("account_background_post is not installed")
        cls.sale_type = cls.env["sale.order.type"].create(
            {
                "name": "Test Background Post Automation",
                "company_id": cls.env.company.id,
                "invoicing_atomation": "validate_invoice",
                "journal_id": cls.company_data["default_journal_sale"].id,
            }
        )
        if cls.env["sale.order"]._fields.get("ignore_exception"):
            cls.env["exception.rule"].search([("active", "=", True)]).write({"active": False})
        cls.service_product = cls.company_data["product_service_order"]
        cls.storable_product = cls.env["product.product"].create(
            {
                "name": "Background Post Storable Product",
                "is_storable": True,
                "type": "consu",
                "invoice_policy": "delivery",
                "list_price": 100.0,
            }
        )

    def _create_so(self, product=None):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "type_id": self.sale_type.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": (product or self.service_product).id,
                            "product_uom_qty": 1.0,
                            "price_unit": 100.0,
                        }
                    )
                ],
            }
        )

    def _confirm_with_ready_pickings(self, count=1):
        orders = self.env["sale.order"]
        for _dummy in range(count):
            order = self._create_so(product=self.storable_product)
            order.action_confirm()
            orders |= order
        for move in orders.picking_ids.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        return orders

    def _failing_post(self):
        return patch.object(
            type(self.env["account.move"]),
            "action_post",
            side_effect=Exception("ARCA timeout"),
        )

    def test_01_confirm_error_aborts_confirmation_and_offers_call_to_action(self):
        so = self._create_so()
        with self._failing_post(), self.assertRaises(RedirectWarning) as catcher:
            so.action_confirm()

        message, action_id, button_text, context = catcher.exception.args
        self.assertIn("ARCA timeout", message)
        self.assertEqual(
            action_id,
            self.env.ref("sale_order_type_automation.action_sale_order_confirm_force_background_post").id,
        )
        self.assertTrue(button_text)
        self.assertEqual(context["active_model"], "sale.order")
        self.assertEqual(context["active_ids"], so.ids)
        self.assertEqual(so.state, "draft", "La orden no debe confirmarse si falló la facturación")

    def test_02_confirm_error_is_logged_on_the_order(self):
        so = self._create_so()
        with self.enter_registry_test_mode(), self._failing_post():
            try:
                so.action_confirm()
            except RedirectWarning:
                pass
            else:
                self.fail("Se esperaba un RedirectWarning")

        so.invalidate_recordset()
        self.assertTrue(
            any("ARCA timeout" in (m.body or "") for m in so.message_ids),
            "Se esperaba el error en el chatter de la orden",
        )

    def test_03_confirm_anyway_defers_invoice_to_background(self):
        so = self._create_so()
        action = so.action_confirm_force_background_post()

        self.assertEqual(so.state, "sale")
        invoice = so.invoice_ids
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, "draft", "La factura queda en borrador para el cron")
        self.assertTrue(invoice.background_post, "La factura queda marcada para validarse en background")
        self.assertEqual(action.get("res_model"), "sale.order")

    def test_04_confirm_anyway_tells_the_invoice_why_it_is_in_draft(self):
        so = self._create_so()
        so.action_confirm_force_background_post()
        invoice = so.invoice_ids

        self.assertTrue(
            any("background post process" in (m.body or "") for m in invoice.message_ids),
            "La factura tiene que explicar por qué quedó en borrador",
        )
        self.assertIn(
            'data-oe-model="sale.order"',
            "".join(m.body or "" for m in invoice.message_ids).replace("'", '"'),
            "Y tiene que apuntar a la orden, donde está el error",
        )
        self.assertTrue(
            any("background post process" in (m.body or "") for m in so.message_ids),
            "La orden también deja registrado que la factura quedó diferida",
        )

    def test_05_background_post_error_is_logged_on_the_order_with_a_pointer_on_the_invoice(self):
        so = self._create_so()
        so.action_confirm_force_background_post()
        invoice = so.invoice_ids
        messages_before = invoice.message_ids

        invoice._notify_background_post_error(Exception("ARCA timeout"))

        self.assertTrue(
            any("ARCA timeout" in (m.body or "") for m in so.message_ids),
            "El error de background post debe registrarse en la orden",
        )
        pointer = invoice.message_ids - messages_before
        self.assertEqual(len(pointer), 1, "La factura debe quedar con un puntero al error")
        self.assertNotIn("ARCA timeout", pointer.body, "El detalle del error va en la orden, no en la factura")
        self.assertIn('data-oe-model="sale.order"', pointer.body.replace("'", '"'))

    def test_06_background_post_error_without_sale_order_falls_back_to_invoice(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [Command.create({"product_id": self.service_product.id, "quantity": 1})],
            }
        )
        invoice._notify_background_post_error(Exception("ARCA timeout"))
        self.assertTrue(any("ARCA timeout" in (m.body or "") for m in invoice.message_ids))

    def test_07_big_picking_batch_creates_invoices_for_background_post(self):
        self.env["ir.config_parameter"].sudo().set_param("account_background_post.batch_size", "1")
        orders = self._confirm_with_ready_pickings(count=2)
        pickings = orders.picking_ids
        self.assertEqual(len(pickings), 2)

        pickings.button_validate()

        self.assertEqual(set(pickings.mapped("state")), {"done"}, "Los pickings deben quedar validados")
        invoices = orders.invoice_ids
        self.assertEqual(len(invoices), 2)
        self.assertEqual(set(invoices.mapped("state")), {"draft"})
        self.assertTrue(all(invoices.mapped("background_post")))

    def test_08_single_picking_error_offers_to_validate_anyway(self):
        self.env["ir.config_parameter"].sudo().set_param("account_background_post.batch_size", "20")
        so = self._confirm_with_ready_pickings()
        picking = so.picking_ids

        with self._failing_post(), self.assertRaises(RedirectWarning) as catcher:
            picking.button_validate()

        message, action_id, dummy_button, context = catcher.exception.args
        self.assertIn("ARCA timeout", message)
        self.assertEqual(
            action_id,
            self.env.ref("sale_order_type_automation.action_picking_validate_force_background_post").id,
        )
        self.assertEqual(context["active_model"], "stock.picking")
        self.assertEqual(context["active_ids"], picking.ids)

    def test_09_validate_anyway_defers_invoice_to_background(self):
        so = self._confirm_with_ready_pickings()
        picking = so.picking_ids

        picking.action_validate_force_background_post()

        self.assertEqual(picking.state, "done")
        invoice = so.invoice_ids
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, "draft")
        self.assertTrue(invoice.background_post)

    def test_10_big_picking_batch_tells_why_the_invoice_is_in_draft(self):
        self.env["ir.config_parameter"].sudo().set_param("account_background_post.batch_size", "1")
        orders = self._confirm_with_ready_pickings(count=2)

        orders.picking_ids.button_validate()

        for order in orders:
            self.assertTrue(
                any("more than 1 transfers" in (m.body or "") for m in order.message_ids),
                "La orden debe explicar por qué la factura quedó en borrador",
            )
            self.assertTrue(
                any("more than 1 transfers" in (m.body or "") for m in order.invoice_ids.message_ids),
                "La factura debe explicar por qué quedó en borrador",
            )

    def test_11_normal_picking_batch_does_not_log_the_batch_reason(self):
        self.env["ir.config_parameter"].sudo().set_param("account_background_post.batch_size", "20")
        so = self._confirm_with_ready_pickings()

        so.picking_ids.button_validate()

        self.assertFalse(
            any("transfers were validated at once" in (m.body or "") for m in so.message_ids),
            "Sin lote grande no hay nada que explicar",
        )

    def test_12_the_batch_flow_keeps_confirming_the_order(self):
        so = self._create_so()

        with self._failing_post(), patch.object(self.env.cr, "commit", lambda: None):
            so.with_context(commit_invoice_automation=True).action_confirm()

        self.assertEqual(so.state, "sale")
        self.assertEqual(so.invoice_ids.state, "draft")
        self.assertTrue(
            any("ARCA timeout" in (m.body or "") for m in so.message_ids),
            "El error tiene que quedar en el chatter de la orden",
        )
