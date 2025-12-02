##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools.safe_eval import safe_eval


class SaleOrderType(models.Model):
    _inherit = "sale.order.type"

    # TODO this should go in a pr to OCA
    sequence_id = fields.Many2one(check_company=True)
    # agregamos help
    journal_id = fields.Many2one(
        help="Billing journal to be used by default. No matter invoice being "
        "created automatically or manually. If no journal is set here, "
        "default journal will be used"
    )
    invoicing_atomation = fields.Selection(
        [
            ("none", "None"),
            ("create_invoice", "Create Invoice"),
            ("validate_invoice", "Validate Invoice"),
            # no estaria funcionando bien, reportado en ticket 18273
            # por ahora desactivamos esta opcion
            # ('try_validate_invoice', 'Try to Validate Invoice (Not recommended)')
        ],
        default="none",
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
        "on invoice validation.",
    )
    payment_atomation = fields.Selection(
        [
            ("none", "None"),
            # TODO ver si implementamos, por ahora solo con validacion
            # porque asi lo implementamos en payment_group
            # ('create_payment', 'Create Payment'),
            ("validate_payment", "Validate Payment"),
        ],
        default="none",
        required=True,
        help="On invoice validation, if:\n"
        "*None: no payment is created\n"
        # "*Create Payment: create payment with journal configured\n"
        "*Validate Payment: create payment and validate it\n",
    )
    picking_atomation = fields.Selection(
        [("none", "None"), ("validate", "Validate"), ("validate_no_force", "Validate No Force")],
        default="none",
        required=True,
        help="Pickings are generated automatically upon sale confirmation.\n"
        'If you set "Validate", '
        "then they will be also confirmed automatically.\n"
        'If you set "Validate No Force", then'
        " Validate without forcing availabilty",
    )
    payment_journal_domain = fields.Binary(compute="_compute_payment_journal_domain")
    payment_journal_id = fields.Many2one(
        "account.journal",
        "Payment Journal",
        domain="payment_journal_domain",
        help="Journal used only with payment_automation. As manual payment "
        "method is used, only journals with manual method are shown. "
        "This field will not be considered for sales coming from eCommerce. "
        "You should configure it directly in Settings > Website.",
        store=True,
        readonly=False,
        compute="_compute_payment_journal_id",
    )
    set_done_on_confirmation = fields.Boolean(
        help="Upon confirmation set"
        " sale order done instead of leaving it on"
        " 'sale order' state that allows modifications"
    )
    auto_done_setting = fields.Boolean(
        compute="_compute_auto_done_setting",
    )
    invoice_validate_domain = fields.Char(
        string="Invoice Validation Domain",
        help="Domain to filter invoices for automatic validation. So, if this filter does NOT find the invoices, they stay in drafts status.",
    )

    @api.depends("payment_atomation")
    def _compute_payment_journal_id(self):
        for rec in self.filtered(lambda x: x.payment_atomation == "none"):
            rec.payment_journal_id = False

    @api.depends("invoice_company_id")
    def _compute_payment_journal_domain(self):
        for rec in self:
            rec.payment_journal_domain = (
                Domain(rec.env["account.journal"]._check_company_domain(rec.invoice_company_id))
                & Domain("type", "in", ["cash", "bank"])
                & Domain("inbound_payment_method_line_ids.code", "=", "manual")
            )

    @api.constrains("invoice_company_id", "payment_journal_id")
    def _check_payment_journal_company(self):
        for rec in self:
            if rec.payment_journal_id and rec.payment_journal_id not in rec.env["account.journal"].search(
                rec.payment_journal_domain
            ):
                raise ValidationError("The selected 'Payment Journal' does not belong to the selected invoice company.")

    @api.depends()
    def _compute_auto_done_setting(self):
        default = self.env["ir.config_parameter"].sudo().get_param("sale.auto_done_setting", "False")
        self.auto_done_setting = safe_eval(default)

    @api.constrains("payment_atomation", "payment_journal_id")
    def validate_invoicing_atomation(self):
        payment_journal_required = self.filtered(lambda x: x.payment_atomation != "none" and not x.payment_journal_id)
        if payment_journal_required:
            raise ValidationError(_("If you choose a Payment automation, Payment Journal " "is required"))

    @api.constrains("journal_id", "payment_journal_id", "sequence_id")
    def validate_company_id(self):
        different_company = self.filtered(
            lambda x: x.invoice_company_id
            and x.payment_journal_id
            and x.invoice_company_id != x.payment_journal_id.company_id
        )
        if different_company:
            raise ValidationError(_("Invoice Journal and Payment Journal must be of the same " "company"))

        # la cia es opcional en la secuencia, solo chequeamos si esta
        # seteada
        # TODO this should go in a pr to OCA sot module
        sequence_diff_company = self.filtered(
            lambda x: x.sequence_id.company_id
            and x.warehouse_id.company_id
            and x.sequence_id.company_id != x.company_id
        )
        if sequence_diff_company:
            raise ValidationError(_("The company of the sequence and the warehouse must be " "the same"))
