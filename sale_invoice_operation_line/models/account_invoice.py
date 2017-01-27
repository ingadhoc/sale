# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import Warning


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    operation_line_ids = fields.One2many(
        'account.invoice.line.operation',
        'invoice_line_id',
        'Operations',
        readonly=True,
    )

    @api.multi
    def _get_operation_percentage(self, operation):
        """For compatibility with sale invoice operation line"""
        self.ensure_one()
        if operation.amount_type == 'percentage':
            operation_line = self.operation_line_ids.search([
                ('operation_id', '=', operation.id),
                ('invoice_line_id', '=', self.id)], limit=1)
            if not operation_line:
                raise Warning(_(
                    'No operation line for line %s and operation %s') % (
                    self.name, operation.display_name))
            return operation_line.percentage
        else:
            # we only have lines for once of type percentage
            return 100.0 - sum(self.operation_line_ids.mapped('percentage'))

    @api.one
    @api.constrains('invoice_id')
    def update_operation_lines(self):
        """
        When creating a new line or when we link an invoice line to an invoice,
        we force the invoice line operations update
        """
        return self.invoice_id.operation_ids.update_operations_lines(
            self)
