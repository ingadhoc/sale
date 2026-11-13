##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "purchase.order.number.mixin"]

    purchase_order_number = fields.Char()

    @api.constrains("state", "purchase_order_number")
    def check_missing_po_number(self):
        invoices_missing_po_number = self.filtered(
            lambda inv: inv.state == "posted"
            and inv.is_sale_document()
            and inv.partner_id.require_purchase_order_number
            and not inv.purchase_order_number
        )
        if invoices_missing_po_number:
            raise UserError(_("You cannot confirm invoice without a" " Purchase Order Number for this partner"))

    def _l10n_cl_purchase_order_reference_applies(self):
        return self.is_sale_document() and self.state == "draft"

    def _l10n_cl_purchase_order_reference_date(self):
        return self.invoice_date or super()._l10n_cl_purchase_order_reference_date()
