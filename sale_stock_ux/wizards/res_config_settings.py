##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    propagate_uom = fields.Boolean(
        'Propagate Unit of Measure',
    )

    def get_values(self):
        res = super().get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(propagate_uom=get_param('stock.propagate_uom', '0') == '1')
        return res

    def set_values(self):
        super().set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('stock.propagate_uom', repr(1 if self.propagate_uom else 0))
