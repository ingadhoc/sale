# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


class SaleOrderLineOperationWizard(models.TransientModel):
    _name = "sale.order.line.operation.wizard"

    @api.model
    def get_order(self):
        return self.env['sale.order'].browse(
            self._context.get('active_id'))

    @api.onchange('order_id')
    def change_order(self):
        self.operation_line_ids = self.order_id.operation_ids.mapped(
            'line_ids')

    order_id = fields.Many2one(
        'sale.order',
        default=get_order,
    )
    operation_line_ids = fields.Many2many(
        'sale.order.line.operation',
        'sale_order_line_wizard_rel',
        'wizard_id', 'operation_line_id',
    )

    @api.multi
    def confirm(self):
        return True
