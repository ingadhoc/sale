##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    require_purchase_order_number = fields.Boolean(
        string="Sale Require Origin",
        related="partner_id.require_purchase_order_number",
    )
    manual_purchase_order_number = fields.Char(
        "PO Number",
    )
    purchase_order_number = fields.Char(
        compute="_compute_purchase_order_number",
        inverse="_inverse_purchase_order_number",
    )

    @api.depends("sale_id")
    def _compute_purchase_order_number(self):
        for rec in self:
            rec.purchase_order_number = (
                rec.manual_purchase_order_number
                if rec.manual_purchase_order_number
                else rec.sale_id.purchase_order_number
            )

    def _inverse_purchase_order_number(self):
        for rec in self:
            rec.manual_purchase_order_number = rec.purchase_order_number

    def _set_l10n_cl_purchase_order_reference(self):
        """In Chile the customer purchase order travels on the delivery guide as an ODC
        cross reference, that l10n_cl_edi_stock builds from client_order_ref. Where this
        module is installed the purchase order number is the field the user fills, so it
        is the one that has to reach the DTE.

        Called from sale.order.action_confirm and not from `_get_new_picking_values`
        because l10n_cl_edi_stock sits above this module in the MRO (it depends on
        l10n_cl_edi, we only depend on sale_stock) and would overwrite what we set
        there. `create` is too early as well: sale_id is not resolved yet.
        """
        if "l10n_cl_reference_ids" not in self._fields:
            return
        purchase_order_doc_type = self.env.ref("l10n_cl.dc_odc", raise_if_not_found=False)
        if not purchase_order_doc_type:
            return
        for picking in self:
            company = picking.company_id
            if (
                not picking.purchase_order_number
                or picking.backorder_id
                or company.account_fiscal_country_id.code != "CL"
                or not company.l10n_cl_dte_service_provider
            ):
                # on a backorder l10n_cl_edi_stock copies the references over, to keep an
                # edit the user made on the original picking
                continue
            references = picking.l10n_cl_reference_ids.filtered(
                lambda ref: ref.l10n_cl_reference_doc_type_id == purchase_order_doc_type
            )
            if not references:
                # client_order_ref was empty, so l10n_cl_edi_stock built no reference
                picking.l10n_cl_reference_ids = [
                    Command.create(
                        {
                            "origin_doc_number": picking.purchase_order_number,
                            "l10n_cl_reference_doc_type_id": purchase_order_doc_type.id,
                            "reason": _("Cross Reference To Purchase Order"),
                            "date": picking.sale_id.date_order or fields.Date.context_today(picking),
                        }
                    )
                ]
                continue
            # only the one built from the sale order, never a value the user typed
            references.filtered(
                lambda ref: ref.origin_doc_number == picking.sale_id.client_order_ref
            ).origin_doc_number = picking.purchase_order_number

    def _action_done(self):
        picking_missing_po_number = self.filtered(
            lambda pick: pick.require_purchase_order_number
            and pick.picking_type_code == "outgoing"
            and not pick.purchase_order_number
        )
        if picking_missing_po_number:
            raise UserError(_("You cannot transfer products without a Purchase Order Number for this partner"))
        return super()._action_done()
