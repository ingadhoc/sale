# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning


class AccountInvoiceLineOperation(models.Model):
    _name = 'account.invoice.line.operation'
    _rec_name = 'percentage'

    operation_id = fields.Many2one(
        'account.invoice.operation',
        'Operation',
        required=True,
        ondelete='cascade',
        readonly=True,
        auto_join=True,
    )
    invoice_line_id = fields.Many2one(
        'account.invoice.line',
        'Invoice Line',
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
            ('invoice_line_id', '=', self.invoice_line_id.id)])
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


class AccountInvoiceOperation(models.Model):
    _inherit = 'account.invoice.operation'

    line_ids = fields.One2many(
        'account.invoice.line.operation',
        'operation_id',
        'Lines'
    )

    @api.multi
    def update_operations_lines(self, model_lines):
        if model_lines._name == 'sale.order.line':
            field = 'sale_line_id'
        elif model_lines._name == 'account.invoice.line':
            field = 'invoice_line_id'
        for operation in self:
            for line in model_lines:
                vals = {
                    'operation_id': operation.id,
                    field: line.id,
                    'percentage': operation.percentage,
                }
                operation_line = line.operation_line_ids.search([
                    ('operation_id', '=', operation.id),
                    (field, '=', line.id),
                ], limit=1)
                if operation_line:
                    operation_line.write(vals)
                else:
                    operation_line.create(vals)
