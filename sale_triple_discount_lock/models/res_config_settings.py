from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    lock_discount1_readonly = fields.Boolean(
        "Lock Discount 1",
        config_parameter="sale_triple_discount_ux.lock_discount1_readonly",
    )
