from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _compute_quantity_returned(self):
        res = super()._compute_quantity_returned()

        pack_parent_lines = self.filtered(
            lambda x: x.pack_child_line_ids
            and x.product_id.pack_ok
            and x.qty_delivered_method == "stock_move"
            and x.product_uom_qty
        )

        for line in pack_parent_lines:
            returned_packs = []
            for pack_line in line.pack_child_line_ids.filtered("product_uom_qty"):
                qty_per_pack = pack_line.product_uom_qty / line.product_uom_qty
                packs_returned = pack_line.quantity_returned / qty_per_pack
                returned_packs.append(packs_returned)

            line.quantity_returned = min(returned_packs) if returned_packs else 0.0

        return res
