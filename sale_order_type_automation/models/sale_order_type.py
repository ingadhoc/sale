# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import ValidationError


class SaleOrderTypology(models.Model):
    _inherit = 'sale.order.type'

    # TODO this should go in a pr to OCA
    sequence_id = fields.Many2one(
        domain="['|', ('company_id', '=', company_id), "
        "('company_id', '=', False)]"
    )
    # agregamos help
    journal_id = fields.Many2one(
        help='Billing journal to be used by default. No matter invoice being '
        'created automatically or manually. If no journal is set here, '
        'default journal will be used'
    )

    invoicing_atomation = fields.Selection([
        ('none', 'None'),
        ('create_invoice', 'Create Invoice'),
        ('validate_invoice', 'Validate Invoice'),
        ('invoice_draft_payment', 'Invoice with Draft Payment'),
        ('invoice_payment', 'Invoice with Payment'),
    ],
        default='none',
        required=True,
        help="On sale order confirmation and on picking confirmation, if:\n"
        "*None: no invoice is created\n"
        "*Create Invoice: create invoice for 'Invoiceable lines' (regarding "
        "product configuration and delivery status)\n"
        "*Validate Invoice: create invoice and validate it\n"
        "*Invoice with Draft Payment: create invoice, validate it and create "
        "payment (on draft)\n"
        "*Invoice with Payment: create invoice, validate it, create payment "
        "and validate it\n"
    )
    picking_atomation = fields.Selection([
        ('none', 'None'),
        ('validate', 'Validate')],
        default='none',
        required=True,
        help='Pickings are generated automatically upon sale confirmation. '
        'If you set "Validate", then they will be also confirmed automatically'
    )
    payment_journal_id = fields.Many2one(
        'account.journal',
        'Payment Journal',
        domain="[('type','in', ['cash', 'bank']),\
        ('company_id', '=', company_id)]",
        help='This journal is only used if "Invoice automation" is set on '
        '"Invoice with Draft Payment" or "Invoice with Payment"\n'
        'IMPORTANT: manual payment method will be used'
    )

    @api.multi
    @api.constrains(
        'journal_id',
        'payment_journal_id')
    def validate_invoicing_atomation(self):
        for rec in self:
            if rec.invoicing_atomation in [
                    'invoice_draft_payment', 'invoice_payment'] and not \
                    rec.payment_journal_id:
                raise ValidationError(_(
                    'If you choose Invoice automation as "Invoice with Draft'
                    ' Payment" or "Invoice with Payment", Payment Journal '
                    'is required'))

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
                raise ValidationError(text % sale_type.journal_id.name)
            if sale_type.payment_journal_id and \
                    sale_type.payment_journal_id.company_id != \
                    sale_type.company_id:
                raise ValidationError(text % sale_type.payment_journal_id.name)
            # la cia es opcional en la secuencia, solo chequeamos si esta
            # seteada
            # TODO this should go in a pr to OCA sot module
            if sale_type.sequence_id.company_id and (
                    sale_type.sequence_id.company_id != sale_type.company_id):
                raise ValidationError(_(
                    'The Sequence "%s" company must be the same than'
                    ' sale order type') % sale_type.sequence_id.name)
