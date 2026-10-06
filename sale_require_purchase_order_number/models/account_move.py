##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = "account.move"

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

    def _set_l10n_cl_purchase_order_reference(self):
        """In Chile the customer purchase order reaches the DTE and the invoice PDF as an
        ODC cross reference. l10n_cl_edi only fills those references by hand or from an
        incoming DTE, so we add ours when the invoice carries a purchase order number.
        """
        if "l10n_cl_reference_ids" not in self._fields:
            return
        purchase_order_doc_type = self.env.ref("l10n_cl.dc_odc", raise_if_not_found=False)
        if not purchase_order_doc_type:
            return
        for move in self:
            company = move.company_id
            if (
                not move.purchase_order_number
                or company.account_fiscal_country_id.code != "CL"
                or not company.l10n_cl_dte_service_provider
            ):
                continue
            # do not add a second one over what the user (or an incoming DTE) already set
            if move.l10n_cl_reference_ids.filtered(
                lambda ref: ref.l10n_cl_reference_doc_type_id == purchase_order_doc_type
            ):
                continue
            move.l10n_cl_reference_ids = [
                Command.create(
                    {
                        "origin_doc_number": move.purchase_order_number,
                        "l10n_cl_reference_doc_type_id": purchase_order_doc_type.id,
                        "reason": _("Cross Reference To Purchase Order"),
                        "date": move.invoice_date or fields.Date.context_today(move),
                    }
                )
            ]
