##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    discount_readonly = fields.Float(
        related='discount',
        readonly=True,
    )
