# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    credit_limit = fields.Float(
        groups='account.group_account_invoice,account.group_account_readonly,portal_sale_distributor.group_portal_backend_distributor')
