##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _create_backorder(self, backorder_moves=None):
        """Inherit to copy book_id to backorder picking"""
        backorders = super()._create_backorder(backorder_moves=backorder_moves)
        for backorder in backorders:
            original_picking = backorder.backorder_id
            if original_picking and original_picking.book_id:
                backorder.book_id = original_picking.book_id
        return backorders
