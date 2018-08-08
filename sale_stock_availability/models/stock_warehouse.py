##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    disable_sale_stock_warning = fields.Boolean(
        help='If true, the warning "Stock availability" is disable',
    )
