# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


class SaleOrderTypology(models.Model):
    _inherit = 'sale.order.type'

    validate_automatically_picking = fields.Boolean(
        'Validate automatically picking',
        help="It will force availability")
    validate_automatically_invoice = fields.Boolean(
        'Validate automatically invoice',)
    payment_journal_id = fields.Many2one(
        'account.journal',
        'Payment Journal',
        domain="[('type','in', ['cash', 'bank'])]"
    )
    validate_automatically_voucher = fields.Boolean(
        'Validate automatically voucher')

    @api.onchange('payment_journal_id')
    def onchange_payment_journal_id(self):
        if self.payment_journal_id:
            self.validate_automatically_invoice = True

    @api.onchange('order_policy')
    def onchange_order_policy(self):
        if self.order_policy != 'manual':
            self.validate_automatically_invoice = False
            self.validate_automatically_picking = False
            self.validate_automatically_voucher = False
            self.payment_journal_id = False
            self.journal_id = False
