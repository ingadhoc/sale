from odoo import models, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.constrains('credit_limit')
    def change_credit_limit(self):
        if not self.env.user.has_group('sale_exception_credit_limit.credit_config'):
            raise ValidationError(_('You are not allowed to edit credit limit field'))
