##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests.common import TransactionCase


class TestConfirmNotificationMail(TransactionCase):
    def _mails(self, order):
        return len(order.message_ids.filtered(lambda m: m.subject == "TEST CONFIRMACION"))

    def test_mail_del_template_solo_si_la_ov_quedo_confirmada(self):
        """El mail del template de presupuesto no sale si la confirmación no dejó la OV en 'sale'."""
        mail_template = self.env["mail.template"].create(
            {
                "name": "Test confirmacion",
                "model_id": self.env.ref("sale.model_sale_order").id,
                "subject": "TEST CONFIRMACION",
                "body_html": "<p>ok</p>",
                "auto_delete": False,
            }
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": self.env["res.partner"].create({"name": "Test"}).id,
                "sale_order_template_id": self.env["sale.order.template"]
                .create({"name": "Template de test", "mail_template_id": mail_template.id})
                .id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.env["product.product"]
                            .create({"name": "Servicio de test", "type": "service"})
                            .id
                        },
                    )
                ],
            }
        )

        # confirmación abortada: la OV sigue en draft y el mail no se manda
        order._send_order_notification_mail(mail_template)
        self.assertEqual(order.state, "draft")
        self.assertEqual(self._mails(order), 0)

        # confirmación real: sale_management lo manda una sola vez
        order.action_confirm()
        self.assertEqual(order.state, "sale")
        self.assertEqual(self._mails(order), 1)
