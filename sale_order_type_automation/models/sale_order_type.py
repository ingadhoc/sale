# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import Warning


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
    validate_automatically_payment = fields.Boolean(
        'Validate automatically payment')

    @api.onchange('payment_journal_id')
    def onchange_payment_journal_id(self):
        if self.payment_journal_id:
            self.validate_automatically_invoice = True

    @api.multi
    @api.constrains(
        'journal_id',
        'payment_journal_id',
        'sequence_id')
    def validate_company_id(self):
        text = _(
            'The Journal "%s" company must be the same than sale order type')
        for sale_type in self:
            if sale_type.journal_id and sale_type.journal_id.company_id\
                    != sale_type.company_id:
                raise Warning(text % sale_type.journal_id.name)
            if sale_type.payment_journal_id and \
                    sale_type.payment_journal_id.company_id != \
                    sale_type.company_id:
                raise Warning(text % sale_type.payment_journal_id.name)
            if sale_type.sequence_id and sale_type.sequence_id.company_id \
                    != sale_type.company_id:
                raise Warning(_(
                    'The Sequence "%s" company must be the same than'
                    ' sale order type') % sale_type.sequence_id.name)
