# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields


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
