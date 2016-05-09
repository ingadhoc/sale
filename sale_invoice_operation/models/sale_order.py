# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    operation_ids = fields.One2many(
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
            in order.operation_ids]
        return vals

    # def onchange_partner_id(self, cr, uid, ids, part, context=None):
    @api.multi
    def onchange_partner_id(self, partner_id):
        result = super(SaleOrder, self).onchange_partner_id(partner_id)
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            if partner.default_sale_invoice_plan:
                plan_vals = partner.default_sale_invoice_plan.get_plan_vals()
                result['value']['operation_ids'] = plan_vals
        return result
