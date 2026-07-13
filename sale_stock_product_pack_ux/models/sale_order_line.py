from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends(
        "pack_child_line_ids.qty_delivered_method",
        "pack_child_line_ids.move_ids.state",
        "pack_child_line_ids.move_ids.scrap_id",
        "pack_child_line_ids.move_ids.product_uom_qty",
        "pack_child_line_ids.move_ids.product_uom",
    )
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
