##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class SaleOrderType(models.Model):
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
    invoice_company_id = fields.Many2one(
        string="Invoice Company",
        related='journal_id.company_id',
    )
    invoicing_atomation = fields.Selection([
        ('none', 'None'),
        ('create_invoice', 'Create Invoice'),
        ('validate_invoice', 'Validate Invoice'),
        # no estaria funcionando bien, reportado en ticket 18273
        # por ahora desactivamos esta opcion
        # ('try_validate_invoice', 'Try to Validate Invoice (Not recommended)')
    ],
        default='none',
        required=True,
        help="On sale order confirmation and on picking confirmation, if:\n"
        "*None: no invoice is created\n"
        "*Create Invoice: create invoice for 'Invoiceable lines' (regarding "
        "product configuration and delivery status)\n"
        "*Validate Invoice: create invoice and validate it\n"
        "*Try to Validate Invoice: create invoice and try to validate it, if "
        "there is a validation error, do not raise it, just log it on SO and "
        "Invoice chatter (invoice will be in draft state till someone validate"
        " it. This option is not recommended because it is less intuiteve for "
        "user. Should only be use if it is common that you are facing errors "
        "on invoice validation."
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
        ('validate', 'Validate'),
        ('validate_no_force', 'Validate No Force')],
        default='none',
        required=True,
        help='Pickings are generated automatically upon sale confirmation.\n'
        'If you set "Validate", '
        'then they will be also confirmed automatically.\n'
        'If you set "Validate No Force", then'
        ' Validate without forcing availabilty'
    )
    payment_journal_id = fields.Many2one(
        'account.journal',
        'Payment Journal',
        domain="[('type','in', ['cash', 'bank']), "
        "('company_id', '=', invoice_company_id), "
        # "('company_id', '=', company_id), "
        "('inbound_payment_method_ids.code', '=', 'manual')]",
        help='Jouranl used only with payment_automation. As manual payment '
        'method is used, only journals with manual method are shown.'
    )
    book_id = fields.Many2one(
        'stock.book',
        'Voucher Book',
    )
    set_done_on_confirmation = fields.Boolean(
        help="Upon confirmation set"
        " sale order done instead of leaving it on"
        " 'sale order' state that allows modifications"
    )
    auto_done_setting = fields.Boolean(
        compute='_compute_auto_done_setting',
    )

    @api.depends()
    def _compute_auto_done_setting(self):
        default = self.env['ir.config_parameter'].sudo().get_param(
            'sale.auto_done_setting', 'False')
        self.auto_done_setting = safe_eval(default)

    @api.constrains(
        'payment_atomation',
        'payment_journal_id')
    def validate_invoicing_atomation(self):
        payment_journal_required = self.filtered(
            lambda x: x.payment_atomation != 'none' and
            not x.payment_journal_id)
        if payment_journal_required:
            raise ValidationError(_(
                'If you choose a Payment automation, Payment Journal '
                'is required'))

    @api.constrains(
        'journal_id',
        'payment_journal_id',
        'sequence_id')
    def validate_company_id(self):
        different_company = self.filtered(
            lambda x: x.invoice_company_id and x.payment_journal_id and
            x.invoice_company_id != x.payment_journal_id.company_id
        )
        if different_company:
            raise ValidationError(_(
                'Invoice Journal and Payment Journal must be of the same '
                'company'))

        # la cia es opcional en la secuencia, solo chequeamos si esta
        # seteada
        # TODO this should go in a pr to OCA sot module
        sequence_diff_company = self.filtered(
            lambda x: x.sequence_id.company_id and
            x.warehouse_id.company_id and
            x.sequence_id.company_id != x.company_id
        )
        if sequence_diff_company:
            raise ValidationError(_(
                'The company of the sequence and the warehouse must be '
                'the same'))
