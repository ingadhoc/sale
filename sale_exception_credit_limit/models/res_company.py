##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_use_credit_limit = fields.Boolean(
        string='Use Credit Limit',
        compute='_compute_account_use_credit_limit',
        store=True,
        readonly=False,
        help="Enable credit limit validation for sales orders",
    )

    @api.depends('parent_id.account_use_credit_limit')
    def _compute_account_use_credit_limit(self):
        for rec in self:
            if rec.parent_id:
                rec.account_use_credit_limit = rec.parent_id.account_use_credit_limit
            # Si no tiene parent, queda como está (editable manualmente)
