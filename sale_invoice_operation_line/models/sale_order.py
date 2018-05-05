##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    operation_line_ids = fields.One2many(
        'sale.order.line.operation',
        'sale_line_id',
        'Operations',
        # copy=True,
        readonly=True,
    )

    @api.one
    @api.constrains('order_id')
    def update_operation_lines(self):
        return self.order_id.operation_ids.update_operations_lines(
            self)
