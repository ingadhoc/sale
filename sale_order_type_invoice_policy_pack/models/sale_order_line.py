##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _compute_qty_to_invoice(self):
        super()._compute_qty_to_invoice()
        main_pack_lines = self.filtered("pack_parent_line_id").mapped("pack_parent_line_id")
        for line in main_pack_lines.filtered(
            lambda sol: sol.order_id.state == "sale" and sol.order_id.type_id.invoice_policy == "delivery"
        ):
            delivered_packs = []
            for pack_line in line.pack_child_line_ids.filtered("product_uom_qty"):
                qty_per_pack = pack_line.product_uom_qty / line.product_uom_qty
                packs_delivered = pack_line.qty_delivered / qty_per_pack
                delivered_packs.append(packs_delivered)

            qty_delivered_packs = min(delivered_packs) if delivered_packs else 0.0
            line.qty_to_invoice = qty_delivered_packs - line.qty_invoiced
