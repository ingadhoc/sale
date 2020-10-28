from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    show_product_image_on_report = fields.Boolean(string="Show Product Image", default=False, config_parameter='sale_ux.show_product_image_on_report')
