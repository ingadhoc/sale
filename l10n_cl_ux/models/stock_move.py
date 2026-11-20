##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_new_picking_values(self):
        # l10n_cl_edi_stock builds the ODC reference from client_order_ref, and skips it when
        # that field is empty: here the purchase order number is the one that reaches SII
        values = super()._get_new_picking_values()
        order = self.sale_line_id.order_id
        if len(order) != 1 or not order._l10n_cl_needs_purchase_order_reference():
            return values
        if references := values.get("l10n_cl_reference_ids"):
            # a copy from the previous picking is kept, the user may have edited it there
            values["l10n_cl_reference_ids"] = [
                Command.create(order._prepare_l10n_cl_purchase_order_reference_vals())
                if command[0] == Command.CREATE
                else command
                for command in references
            ]
            return values
        purchase_order_doc_type = self.env.ref("l10n_cl.dc_odc")
        previous_references = self.move_orig_ids.picking_id.l10n_cl_reference_ids.filtered(
            lambda ref: ref.l10n_cl_reference_doc_type_id == purchase_order_doc_type
        )
        values["l10n_cl_reference_ids"] = [Command.link(ref.copy().id) for ref in previous_references] or [
            Command.create(order._prepare_l10n_cl_purchase_order_reference_vals())
        ]
        return values
