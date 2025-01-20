##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models
from odoo.exceptions import ValidationError


class WhatsAppComposer(models.TransientModel):

    _inherit = 'whatsapp.composer'

    def action_send_whatsapp_template(self):
        if self.phone:
            if self.phone.startswith("+54"):
                if len(self.phone) > 3 and self.phone[3] == "9":
                    super().action_send_whatsapp_template()
                else:
                    raise ValidationError('El formato del número de Argentina %s debe contener un 9 a continuación del +54.' % (self.phone))
