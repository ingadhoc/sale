##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    require_purchase_order_number = fields.Boolean(
        string='Sale Require Origin',
        related='partner_id.require_purchase_order_number',
    )
    purchase_order_number = fields.Char(
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    @api.multi
    def invoice_validate(self):
        invoices_missing_po_number = self.filtered(
            lambda inv: inv.require_purchase_order_number and inv.type
            in ['out_invoice', 'out_refund']
            and not inv.purchase_order_number)
        if invoices_missing_po_number:
            raise UserError(_(
                'You cannot confirm invoice without a'
                ' Purchase Order Number for this partner'))
        return super().invoice_validate()
