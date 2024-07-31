from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_auto_done_setting = fields.Boolean(group='base.group_user,base.group_portal')
