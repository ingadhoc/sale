##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "purchase.order.number.mixin"]

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

    def _l10n_cl_purchase_order_reference_applies(self):
        # on a backorder l10n_cl_edi_stock copies the references over, to keep an edit the
        # user made on the original picking; a done picking may already have its DTE
        return self.picking_type_code == "outgoing" and self.state not in ("done", "cancel") and not self.backorder_id

    def _l10n_cl_purchase_order_reference_date(self):
        if self.sale_id.date_order:
            return fields.Date.context_today(self, self.sale_id.date_order)
        return super()._l10n_cl_purchase_order_reference_date()

    def _l10n_cl_update_purchase_order_reference(self, references):
        # only the one built from client_order_ref by l10n_cl_edi_stock, never a value the user typed
        references.filtered(
            lambda ref: ref.origin_doc_number == self.sale_id.client_order_ref
        ).origin_doc_number = self.purchase_order_number

    def _action_done(self):
        picking_missing_po_number = self.filtered(
            lambda pick: pick.require_purchase_order_number
            and pick.picking_type_code == "outgoing"
            and not pick.purchase_order_number
        )
        if picking_missing_po_number:
            raise UserError(_("You cannot transfer products without a Purchase Order Number for this partner"))
        return super()._action_done()
