##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests.common import TransactionCase


class TestConfirmNotificationMail(TransactionCase):

    def test_ignorar_excepcion_manda_un_solo_mail(self):
        """Ignorar una excepción confirma la OV y manda el mail una sola vez."""
        self.env['exception.rule'].search([]).write({'active': False})
        self.env['exception.rule'].create({
            'name': 'Regla de test',
            'model': 'sale.order',
            'exception_type': 'by_py_code',
            'code': 'failed = True',
        })
        mail_template = self.env['mail.template'].create({
            'name': 'Test confirmacion',
            'model_id': self.env.ref('sale.model_sale_order').id,
            'subject': 'TEST CONFIRMACION',
            'body_html': '<p>ok</p>',
            'auto_delete': False,
        })
        order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test'}).id,
            'sale_order_template_id': self.env['sale.order.template'].create({
                'name': 'Template de test',
                'mail_template_id': mail_template.id,
            }).id,
            'order_line': [(0, 0, {
                'product_id': self.env['product.product'].create({
                    'name': 'Servicio de test',
                    'type': 'service',
                }).id,
            })],
        })

        order.action_confirm()
        self.env['sale.exception.confirm'].with_context(
            active_id=order.id,
            active_ids=order.ids,
            active_model=order._name,
        ).create({'ignore': True}).action_confirm()

        self.assertEqual(order.state, 'sale')
        self.assertEqual(len(order.message_ids.filtered(
            lambda m: m.subject == 'TEST CONFIRMACION')), 1)
