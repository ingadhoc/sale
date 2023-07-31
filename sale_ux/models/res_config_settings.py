from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    analytic_account_without_company = fields.Boolean(
        'Crear cuenta analitica sin compañía',
        config_parameter='sale_ux.analytic_account_without_company'
    )
