##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import new_test_user, tagged


@tagged("post_install", "-at_install")
class TestBatchInvoiceNotifications(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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

    def test_batch_invoicing_queues_assignment_notifications(self):
        orders = self._create_confirmed_order(self.partner_a) + self._create_confirmed_order(self.partner_b)
        self.env["sale.advance.payment.inv"].with_context(
            active_model="sale.order",
            active_ids=orders.ids,
            tracking_disable=False,
            mail_create_nosubscribe=False,
            mail_notrack=False,
        ).create({}).create_invoices()

        invoices = orders.invoice_ids
        self.assertEqual(len(invoices), 2)
        mails = self.env["mail.mail"].search(
            [
                ("model", "=", "account.move"),
                ("res_id", "in", invoices.ids),
                ("recipient_ids", "in", self.salesman.partner_id.ids),
            ]
        )
        self.assertEqual(len(mails), 2, "Each invoice must notify its salesman")
        self.assertEqual(set(mails.mapped("state")), {"outgoing"}, "Notifications must wait in the mail queue")
