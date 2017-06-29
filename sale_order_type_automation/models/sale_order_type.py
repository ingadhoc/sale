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
    ],
        default='none',
        required=True,
        help="On sale order confirmation and on picking confirmation, if:\n"
        "*None: no invoice is created\n"
        "*Create Invoice: create invoice for 'Invoiceable lines' (regarding "
        "product configuration and delivery status)\n"
        "*Validate Invoice: create invoice and validate it\n"
    )
    payment_atomation = fields.Selection([
        ('none', 'None'),
        # TODO ver si implementamos, por ahora solo con validacion
        # porque asi lo implementamos en payment_group
        # ('create_payment', 'Create Payment'),
        ('validate_payment', 'Validate Payment'),
    ],
        default='none',
        required=True,
        help="On invoice validation, if:\n"
        "*None: no payment is created\n"
        # "*Create Payment: create payment with journal configured\n"
        "*Validate Payment: create payment and validate it\n"
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
        domain="[('type','in', ['cash', 'bank']), "
        "('company_id', '=', company_id), "
        "('inbound_payment_method_ids.code', '=', 'manual')]",
        help='Jouranl used only with payment_automation. As manual payment '
        'method is used, only journals with manual method are shown.'
    )
    book_id = fields.Many2one(
        'stock.book',
        'Voucher Book',
    )

    @api.multi
    @api.constrains(
        'payment_atomation',
        'payment_journal_id')
    def validate_invoicing_atomation(self):
        for rec in self:
            if rec.payment_atomation != 'none' and not rec.payment_journal_id:
                raise ValidationError(_(
                    'If you choose a Payment automation, Payment Journal '
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
