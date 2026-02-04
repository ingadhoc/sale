##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_use_credit_limit = fields.Boolean(
        string='Use Credit Limit',
        compute='_compute_account_use_credit_limit',
        inverse='_inverse_account_use_credit_limit',
        readonly=False,
    )

    is_root_company = fields.Boolean(
        compute='_compute_is_root_company',
        string='Is Root Company',
    )

    @api.depends('company_id', 'company_id.account_use_credit_limit')
    def _compute_account_use_credit_limit(self):
        for rec in self:
            rec.account_use_credit_limit = rec.company_id.account_use_credit_limit

    def _inverse_account_use_credit_limit(self):
        for rec in self:
            # Solo permitir cambiar si es root company
            if not rec.company_id.parent_id:
                rec.company_id.account_use_credit_limit = rec.account_use_credit_limit

    @api.depends('company_id', 'company_id.parent_id')
    def _compute_is_root_company(self):
        for rec in self:
            rec.is_root_company = not rec.company_id.parent_id
