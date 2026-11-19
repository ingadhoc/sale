##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command, _, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _l10n_cl_needs_purchase_order_reference(self):
        self.ensure_one()
        company = self.company_id
        return bool(
            self.purchase_order_number
            and company.account_fiscal_country_id.code == "CL"
            and company.l10n_cl_dte_service_provider
        )

    def _prepare_l10n_cl_purchase_order_reference_vals(self):
        self.ensure_one()
        return {
            "origin_doc_number": self.purchase_order_number,
            "l10n_cl_reference_doc_type_id": self.env.ref("l10n_cl.dc_odc").id,
            "reason": _("Cross Reference To Purchase Order"),
            "date": fields.Date.context_today(self, self.date_order),
        }

    def _create_invoices(self, grouped=False, final=False, date=None):
        # l10n_cl_edi only fills the invoice references by hand or from an incoming DTE
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        purchase_order_doc_type = self.env.ref("l10n_cl.dc_odc")
        for move in moves.filtered(lambda m: m.move_type == "out_invoice"):
            if move.l10n_cl_reference_ids.filtered(
                lambda ref: ref.l10n_cl_reference_doc_type_id == purchase_order_doc_type
            ):
                continue
            orders = move.line_ids.sale_line_ids.order_id.filtered(
                lambda order: order._l10n_cl_needs_purchase_order_reference()
            )
            move.l10n_cl_reference_ids = [
                Command.create(order._prepare_l10n_cl_purchase_order_reference_vals()) for order in orders
            ]
        return moves
