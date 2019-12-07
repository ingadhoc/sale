from odoo import models, api


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    def _message_auto_subscribe_notify(self, partner_ids, template):
        """ Cuando usuario portal crea OV se manda un mensjae de suscripcion
        al comercial, esto terminahaciendo que se arroje error si se tiene
        instalado mass_mailing y las estadisticas por permiso de acceso
        a estadisticas. De esta forma lo arreglamos para que no haga falta
        modulo puente
        """
        if self._name == 'sale.order' and \
                not self.env.user.has_group('base.group_user'):
            self = self.sudo()
        return super(MailThread, self)._message_auto_subscribe_notify(partner_ids, template)
