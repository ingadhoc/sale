from odoo import models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _message_auto_subscribe(self, updated_values, followers_existing_policy='skip'):
        """ Cuando usuario portal crea OV se manda un mensjae de suscripcion
        al comercial, esto terminahaciendo que se arroje error si se tiene
        instalado mass_mailing y las estadisticas por permiso de acceso
        a estadisticas. De esta forma lo arreglamos para que no haga falta
        modulo puente
        """
        if self._name == 'sale.order' and \
                not self.env.user.has_group('base.group_user'):
            self = self.sudo()

        return super()._message_auto_subscribe(updated_values, followers_existing_policy=followers_existing_policy)
