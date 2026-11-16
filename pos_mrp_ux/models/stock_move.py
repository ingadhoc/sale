from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _add_mls_related_to_order(self, related_order_lines, are_qties_done=True):
        # The order lines carry the lots the cashier picked for what was sold
        # loose, not for the components of a kit. Letting them reach the
        # exploded move repeats its whole demand once per line and per lot, so
        # the move ends up over its demand. We assign it like any other kit
        # move instead.
        kit_moves = self.filtered("bom_line_id")
        res = super(StockMove, self - kit_moves)._add_mls_related_to_order(
            related_order_lines, are_qties_done=are_qties_done
        )
        for move in kit_moves:
            move.quantity = move.product_uom_qty
        return res
