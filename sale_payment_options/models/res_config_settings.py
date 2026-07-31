from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sale_payment_options_by_line = fields.Boolean(related="company_id.sale_payment_options_by_line", readonly=False)
