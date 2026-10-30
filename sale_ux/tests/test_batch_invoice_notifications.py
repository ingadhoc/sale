##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from unittest.mock import patch

from odoo import Command
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import new_test_user, tagged


@tagged("post_install", "-at_install")
class TestBatchInvoiceNotifications(TestSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # sale_exception rolls back the whole transaction inside action_confirm when a rule matches
        if "exception.rule" in cls.env:
            cls.env["exception.rule"].sudo().search([]).write({"active": False})
        cls.salesman = new_test_user(
            cls.env,
            login="batch_invoice_salesman",
            groups="sales_team.group_sale_salesman",
            email="batch.salesman@example.com",
            notification_type="email",
        )
        cls.product = cls._create_product(name="Batch invoice product", type="consu", invoice_policy="order")

    def _create_confirmed_order(self, partner):
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "user_id": self.salesman.id,
                "order_line": [
                    Command.create({"product_id": self.product.id, "product_uom_qty": 1, "price_unit": 100})
                ],
            }
        )
        order.action_confirm()
        return order

    def _invoice_and_get_mails(self, orders):
        # Since 19.0 mail.mail._send does nothing in tests, so watch which mails are sent instead of their state
        MailMail = self.env.registry["mail.mail"]
        with patch.object(MailMail, "send", autospec=True, return_value=True) as send:
            self.env["sale.advance.payment.inv"].with_context(
                active_model="sale.order",
                active_ids=orders.ids,
                tracking_disable=False,
                mail_create_nosubscribe=False,
                mail_notrack=False,
            ).create({}).create_invoices()
        invoices = orders.invoice_ids
        self.assertEqual(len(invoices), len(orders))
        notifications = self.env["mail.message"].search(
            [
                ("model", "=", "account.move"),
                ("res_id", "in", invoices.ids),
                ("message_type", "=", "user_notification"),
                ("partner_ids", "in", self.salesman.partner_id.ids),
            ]
        )
        self.assertEqual(len(notifications), len(invoices), "Each invoice must notify its salesman")
        mails = self.env["mail.mail"].search([("mail_message_id", "in", notifications.ids)])
        self.assertEqual(len(mails), len(invoices))
        sent = self.env["mail.mail"].browse([mail_id for call in send.call_args_list for mail_id in call.args[0].ids])
        return mails, sent

    def test_batch_invoicing_queues_assignment_notifications(self):
        orders = self._create_confirmed_order(self.partner_a) + self._create_confirmed_order(self.partner_b)
        mails, sent = self._invoice_and_get_mails(orders)
        self.assertFalse(mails & sent, "Notifications must wait in the mail queue")
        self.assertEqual(set(mails.mapped("state")), {"outgoing"})

    def test_single_order_invoicing_sends_assignment_notification(self):
        mails, sent = self._invoice_and_get_mails(self._create_confirmed_order(self.partner_a))
        self.assertEqual(mails & sent, mails, "The notification must be sent right away")
