from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_billing_behavior = fields.Selection(related="pos_config_id.billing_behavior", readonly=False)
    pos_block_invoice_download = fields.Boolean(related="pos_config_id.block_invoice_download", readonly=False)
    pos_default_partner_id = fields.Many2one(related="pos_config_id.default_partner_id", readonly=False)
