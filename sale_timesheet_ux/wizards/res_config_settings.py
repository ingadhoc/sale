from odoo import models, fields


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    timesheet_protect_so_line = fields.Boolean(
        string="Protect SO Line on Timesheets?", default=False, config_parameter='sale_timesheet_ux.protect_so_line')
