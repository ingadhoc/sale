##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class SaleOrderTypology(models.Model):
    _inherit = 'sale.order.type'

    invoice_policy = fields.Selection([
        ('by_product', 'Defined by Product'),
        ('prepaid', 'Before Delivery'),
        ('order', 'Ordered quantities')
        # TODO habria que implementarlo
        # ('delivery', 'Delivered quantities'),
    ],
        string='Invoicing Policy',
        required=True,
        default='by_product',
        help='If you choose prepaid you...'
    )
