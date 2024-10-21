from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_auto_done_setting = fields.Boolean(group='base.group_user,portal_sale_distributor.group_portal_backend_distributor')
