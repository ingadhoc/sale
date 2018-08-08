##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    type_id = fields.Many2one(
        track_visibility='onchange',
        readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
    )
