# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import Warning


class SaleInvoiceOperation(models.Model):
    _inherit = 'account.invoice.operation'
    _name = 'sale.invoice.operation'

    # only required on invoice operation, not in sale operations
    invoice_id = fields.Many2one(
        required=False,
        auto_join=True,
    )
    order_id = fields.Many2one(
        'sale.order',
        'Sale Order',
        auto_join=True,
        ondelete='cascade',
        required=True,
    )

    # we dont need this check because we keep original currency
    # @api.one
    # @api.constrains('order_id', 'journal_id', 'company_id')
    # def check_currencies(self):
    #     other_currency = (
    #         self.journal_id.currency or self.company_id.currency_id)
    #     if other_currency and self.order_id.currency_id != other_currency:
    #         raise Warning(_(
    #             'You can not use a journal or company of different currency '
    #             'than sale order currency. Operation "%s"') % (
    #                 self.display_name))

    @api.multi
    @api.depends('sequence', 'order_id')
    def get_number(self):
        for order in self.mapped('order_id'):
            number = 1
            operations = order.operation_ids.search([
                ('order_id', '=', order.id), ('id', 'in', self.ids)])
            for operation in operations:
                operation.number = number
                number += 1
