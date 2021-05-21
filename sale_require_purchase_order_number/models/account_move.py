##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = "account.move"

    purchase_order_number = fields.Char(
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    @api.constrains('state', 'purchase_order_number')
    def check_missing_po_number(self):
        invoices_missing_po_number = self.filtered(
            lambda inv: inv.state == 'posted' and inv.is_sale_document()
            and inv.partner_id.require_purchase_order_number and not inv.purchase_order_number)
        if invoices_missing_po_number:
            raise UserError(_(
                'You cannot confirm invoice without a'
                ' Purchase Order Number for this partner'))
