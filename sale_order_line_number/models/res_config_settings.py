##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    number_sale_order_line = fields.Boolean(
        config_parameter='sale_order_line_number.number_sale_order_line'
    )
