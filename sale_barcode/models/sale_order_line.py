##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class SaleOrderLine(models.Model):

    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'barcodes.barcode_events_mixin']

    product_barcode = fields.Char(related='product_id.barcode')
