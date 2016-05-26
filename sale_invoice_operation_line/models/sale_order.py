# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


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
