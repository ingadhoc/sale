##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    # Use this field to avoid an error in the domain using relation of fields.
    commercial_partner_id = fields.Many2one(
        string='Commercial Partner',
        related='partner_id.commercial_partner_id',
        store=True,
    )
