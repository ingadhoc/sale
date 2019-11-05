##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    restrict_sales = fields.Selection(
        related='company_id.restrict_sales',
        readonly=False,
    )
    restrict_sales_amount = fields.Float(
        related='company_id.restrict_sales_amount',
        readonly=False,
    )
