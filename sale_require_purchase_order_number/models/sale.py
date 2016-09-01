# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import Warning


class sale_order(models.Model):
    _inherit = "sale.order"

    require_purchase_order_number = fields.Boolean(
        string='Sale Require Origin',
        related='partner_id.require_purchase_order_number')
    purchase_order_number = fields.Char(
        'Purchase Order Number')

    _sql_constraints = [
        ('purchase_order_number_uniq', 'unique (purchase_order_number, partner_id)',
         'The Purchase Order Number must be unique!')
    ]

    @api.multi
    def action_confirm(self):
        if self.require_purchase_order_number:
            if not self.purchase_order_number:
                raise Warning(_(
                    'You cannot confirm a sales order without a'
                    ' Purchase Order Number for this partner'))
        return super(sale_order, self).action_confirm()

    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(sale_order, self)._prepare_invoice()
        invoice_vals.update({
            'purchase_order_number': self.purchase_order_number})
        return invoice_vals
