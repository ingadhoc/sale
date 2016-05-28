# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


class SaleOrderLineOperation(models.Model):
    _inherit = 'account.invoice.line.operation'
    _name = 'sale.order.line.operation'

    operation_id = fields.Many2one(
        'sale.invoice.operation',
    )
    invoice_line_id = fields.Many2one(
        required=False,
    )
    sale_line_id = fields.Many2one(
        'sale.order.line',
        'Sale Order Line',
        ondelete='cascade',
        readonly=True,
        auto_join=True,
    )

    @api.one
    @api.constrains('operation_id', 'percentage')
    def check_percetantage(self):
        return self._check_percetantage(
            'sale_line_id',
            self.sale_line_id.operation_line_ids,
            self.sale_line_id.order_id.operation_ids)


class SaleInvoiceOperation(models.Model):
    # we reinherit account invoice operation for new function
    _inherit = ['account.invoice.operation', 'sale.invoice.operation']
    _name = 'sale.invoice.operation'

    line_ids = fields.One2many(
        'sale.order.line.operation',
        'operation_id',
        'Lines',
    )

    @api.multi
    def get_operations_vals(self):
        vals = super(SaleInvoiceOperation, self).get_operations_vals()
        lines = self._context.get('invoice_line_ids', [])
        line_vals = []
        for inv_line_id in lines:
            so_operation_line = self.env[
                'sale.order.line.operation'].search([
                    ('sale_line_id.invoice_lines', 'in', [inv_line_id]),
                    ('operation_id', '=', self.id),
                ])
            if len(so_operation_line) != 1:
                # TODO analizar si queremos lanzar error o permitimos que no
                # haya operaciones sin operation line
                continue
                # raise Warning(_(
                #     'No operation line found on sale order %s for '
                #     'operation %s') % (
                # self.order_id.name, self.display_name))
            line_vals.append((0, 0, {
                'invoice_line_id': inv_line_id,
                'percentage': so_operation_line.percentage,
            }))
        vals.update({
            'line_ids': line_vals,
        })
        return vals

    @api.multi
    def _run_checks(self):
        self.update_operations_lines(
            self.mapped('order_id.order_line'))
        return super(SaleInvoiceOperation, self)._run_checks()
