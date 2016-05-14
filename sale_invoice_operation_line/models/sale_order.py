# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


# class SaleOrder(models.Model):
#     _inherit = 'sale.order'

#     @api.multi
#     def update_operations_lines(self):
#         return self.operation_ids.update_operations_lines(
#             self.order_line)

#     @api.one
#     @api.constrains('operation_ids')
#     def change_operations(self):
#         self.operation_ids.update_operations_lines(
#             self.order_line)
#     @api.onchange('operation_ids')
#     def change_operations(self):
#         if self.order_line:
#             return {'warning': {
#                 'title': _('Operations Warning!'),
#                 'message': _('If you change the operations of this order '
#                     'operations lines will not be updated.')
#             }}

#     TODO analizar si al confirmar chequemos que todas las lineas tengan su
#     operation y/o si chequemos por porcentaje
#     @api.multi
#     def action_button_confirm(self):
#         self.ensure_one()
#         for operation in self.operation_ids:
#             operation.with_context(invoice_line_ids=lines).get_operations_vals()
#         return super(SaleOrder, self).action_button_confirm()


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
