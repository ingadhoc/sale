# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


class AccountInvoiceLineOperationWizard(models.TransientModel):
    _name = "account.invoice.line.operation.wizard"

    @api.model
    def get_invoice(self):
        return self.env['account.invoice'].browse(
            self._context.get('active_id'))

    @api.onchange('invoice_id')
    def change_invoice(self):
        self.operation_line_ids = self.invoice_id.operation_ids.mapped(
            'line_ids')

    invoice_id = fields.Many2one(
        'account.invoice',
        default=get_invoice,
    )
    operation_line_ids = fields.Many2many(
        'account.invoice.line.operation',
        'account_invoice_line_wizard_rel',
        'wizard_id', 'operation_line_id',
    )

    @api.multi
    def confirm(self):
        return True
