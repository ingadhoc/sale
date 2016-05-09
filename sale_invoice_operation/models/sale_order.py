# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    invoice_operation_ids = fields.One2many(
        'sale.invoice.operation',
        'order_id',
        'Invoice Operations',
        readonly=True,
        copy=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
    )

    @api.model
    def _prepare_invoice(self, order, lines):
        vals = super(SaleOrder, self)._prepare_invoice(
            order, lines)
        # we send invoice_line_ids for compatibility with operation line
        vals['operation_ids'] = [
            (0, 0, x.with_context(
                invoice_line_ids=lines).get_operations_vals()) for x
            in order.invoice_operation_ids]
        return vals
