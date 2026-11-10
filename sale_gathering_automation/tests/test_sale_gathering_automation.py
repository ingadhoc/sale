##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import odoo.tests.common as common
from odoo.fields import Command


class TestSaleGatheringAutomation(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create({"name": "Gathering Automation Partner"})
        # a manual service line is delivered by the picking automation without any stock move
        self.product = self.env["product.product"].create(
            {
                "name": "Gathering Automation Service",
                "type": "service",
                "service_type": "manual",
                "invoice_policy": "order",
                "list_price": 100.0,
                "taxes_id": [Command.clear()],
            }
        )
        self.journal = self.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        if self.env["sale.order"]._fields.get("ignore_exception"):
            self.env["exception.rule"].search([("active", "=", True)]).write({"active": False})
        if "loyalty.program" in self.env:
            self.env["loyalty.program"].search([("active", "=", True)]).write({"active": False})

    def _type(self, **values):
        return self.env["sale.order.type"].create(
            dict(
                {
                    "name": "Gathering Automation Type",
                    "company_id": self.env.company.id,
                    "journal_id": self.journal.id,
                },
                **values,
            )
        )

    def _order(self, order_type, is_gathering=True, qty=5.0):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "type_id": order_type.id,
                "is_gathering": is_gathering,
                "order_line": [
                    Command.create({"product_id": self.product.id, "product_uom_qty": qty, "price_unit": 100.0})
                ],
            }
        )

    def _gathered_order(self, order_type):
        """A confirmed gathering order with its gathering invoice posted and paid.

        Withdrawing is blocked by `sale_gathering` until that invoice is paid.
        """
        order = self._order(order_type)
        line = order.order_line
        order.action_confirm()
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=order.invoice_ids.ids
        ).create({})._create_payments()
        return order, line

    def test_the_gathering_invoice_is_created_on_confirm(self):
        order = self._order(self._type(invoicing_atomation="create_invoice"))

        order.action_confirm()

        self.assertEqual(len(order.invoice_ids), 1)
        self.assertTrue(order.has_gathering_invoice)
        self.assertEqual(order.invoice_ids.state, "draft")
        self.assertAlmostEqual(order.invoice_ids.amount_total, 500.0)
        self.assertAlmostEqual(order.gathering_amount_with_taxes, 500.0)

    def test_without_automation_the_order_gets_no_gathering_invoice(self):
        order = self._order(self._type(invoicing_atomation="none"))

        order.action_confirm()

        self.assertFalse(order.invoice_ids)
        self.assertFalse(order.has_gathering_invoice)

    def test_the_gathering_invoice_is_posted_when_the_domain_does_not_match(self):
        order = self._order(
            self._type(
                invoicing_atomation="validate_invoice",
                invoice_validate_domain="[('move_type', '=', 'in_invoice')]",
            )
        )

        order.action_confirm()

        self.assertEqual(order.invoice_ids.state, "posted")

    def test_the_create_invoice_button_runs_the_automation(self):
        order, line = self._gathered_order(self._type(invoicing_atomation="validate_invoice"))
        # the withdrawal: what the customer takes out of the gathered quantity
        order.write({"order_line": [Command.update(line.id, {"product_uom_qty": 2.0})]})

        action = order.action_create_invoice_with_automation()

        self.assertEqual(action["res_model"], "account.move")
        self.assertEqual(len(order.invoice_ids), 2)

    def test_the_create_invoice_button_opens_the_wizard_without_automation(self):
        order = self._order(self._type(invoicing_atomation="none"), is_gathering=False)
        order.action_confirm()

        action = order.action_create_invoice_with_automation()

        self.assertEqual(action["res_model"], "sale.advance.payment.inv")

    def test_a_quantity_change_runs_the_picking_automation(self):
        order, line = self._gathered_order(
            self._type(invoicing_atomation="validate_invoice", picking_atomation="validate")
        )
        self.assertEqual(line.qty_delivered, 0.0)

        order.write({"order_line": [Command.update(line.id, {"product_uom_qty": 3.0})]})

        self.assertEqual(line.qty_delivered, 3.0)

    def test_only_a_quantity_tells_the_automation_to_run(self):
        order = self._order(self._type(invoicing_atomation="none"))
        line = order.order_line

        self.assertFalse(order._has_quantity_changes({"client_order_ref": "ABC"}))
        self.assertFalse(order._has_quantity_changes({"order_line": [Command.update(line.id, {"discount": 10.0})]}))
        self.assertTrue(
            order._has_quantity_changes({"order_line": [Command.update(line.id, {"product_uom_qty": 1.0})]})
        )
        self.assertTrue(
            order._has_quantity_changes(
                {"order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 1.0})]}
            )
        )
