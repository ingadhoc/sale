# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp


class SaleOrderLineOperation(models.Model):
    _name = 'sale.order.line.operation'
    _rec_name = 'percentage'

    operation_id = fields.Many2one(
        'sale.invoice.operation',
        'Operation',
        required=True,
        ondelete='cascade',
        readonly=True,
        auto_join=True,
    )
    sale_line_id = fields.Many2one(
        'sale.order.line',
        'Sale Order Line',
        ondelete='cascade',
        readonly=True,
        auto_join=True,
    )
    percentage = fields.Float(
        'Percentage',
        digits=dp.get_precision('Discount'),
    )

    @api.one
    @api.constrains('operation_id', 'percentage')
    def check_percetantage(self):
        operation_lines = self.search([
            ('operation_id', '=', self.operation_id.id),
            ('sale_line_id', '=', self.sale_line_id.id)])
        msg = _('Sum of percentage could not be greater than 100%')
        op_lines_percentage = sum(operation_lines.mapped('percentage'))
        if op_lines_percentage > 100.0:
            raise Warning(msg)

        # TODO ver si incorporamos esta restriccion, da error al hacer load
        # de una del 100%
        # invoice_op_percentage = sum(
        #     self.operation_id.invoice_id.operation_ids.mapped('percentage'))

        # if invoice_op_percentage == 100.0 and op_lines_percentage != 100.0:
        #     raise Warning(_(
        #         'If Invoice Operations sum is 100%, then lines must also sum'
        #         ' 100%'))


class SaleInvoiceOperation(models.Model):
    # we reinherit account invoice operation for new function
    _inherit = ['account.invoice.operation', 'sale.invoice.operation']
    _name = 'sale.invoice.operation'

    line_ids = fields.One2many(
        'sale.order.line.operation',
        'operation_id',
        'Lines'
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
                raise Warning(_(
                    'No operation line found on sale order %s for '
                    'operation %s') % (self.order_id.name, self.display_name))
            line_vals.append((0, 0, {
                'invoice_line_id': inv_line_id,
                'percentage': so_operation_line.percentage,
            }))
        vals.update({
            'line_ids': line_vals,
        })
        return vals
