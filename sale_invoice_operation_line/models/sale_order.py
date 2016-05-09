# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def update_operations_lines(self):
        return self.operation_ids.update_operations_lines(
            self.order_line)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    operation_line_ids = fields.One2many(
        'sale.order.line.operation',
        'sale_line_id',
        'Operations',
        copy=True,
    )
