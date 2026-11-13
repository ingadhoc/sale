##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command, _, fields, models


class PurchaseOrderNumberMixin(models.AbstractModel):
    _name = "purchase.order.number.mixin"
    _description = "Purchase Order Number Chilean Reference"

    def _set_l10n_cl_purchase_order_reference(self):
        """In Chile the customer purchase order reaches the DTE and the PDF as an ODC cross
        reference. Where this module is installed the purchase order number is the field the
        user fills, so it is the one that has to reach SII.
        """
        if "l10n_cl_reference_ids" not in self._fields:
            return
        purchase_order_doc_type = self.env.ref("l10n_cl.dc_odc", raise_if_not_found=False)
        if not purchase_order_doc_type:
            return
        for rec in self:
            company = rec.company_id
            if (
                not rec.purchase_order_number
                or company.account_fiscal_country_id.code != "CL"
                or not company.l10n_cl_dte_service_provider
                or not rec._l10n_cl_purchase_order_reference_applies()
            ):
                continue
            references = rec.l10n_cl_reference_ids.filtered(
                lambda ref: ref.l10n_cl_reference_doc_type_id == purchase_order_doc_type
            )
            if references:
                rec._l10n_cl_update_purchase_order_reference(references)
                continue
            rec.l10n_cl_reference_ids = [
                Command.create(
                    {
                        "origin_doc_number": rec.purchase_order_number,
                        "l10n_cl_reference_doc_type_id": purchase_order_doc_type.id,
                        "reason": _("Cross Reference To Purchase Order"),
                        "date": rec._l10n_cl_purchase_order_reference_date(),
                    }
                )
            ]

    def _l10n_cl_purchase_order_reference_applies(self):
        return True

    def _l10n_cl_purchase_order_reference_date(self):
        return fields.Date.context_today(self)

    def _l10n_cl_update_purchase_order_reference(self, references):
        """By default an existing reference is kept, whoever set it."""
