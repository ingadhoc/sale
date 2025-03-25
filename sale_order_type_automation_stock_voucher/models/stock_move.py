##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _assign_picking(self):
        res = super()._assign_picking()
        for rec in self.sudo().filtered(
            lambda x: x.picking_id.sale_id.type_id and x.picking_id.sale_id.type_id.book_id
        ):
            rec.picking_id.write({"book_id": rec.picking_id.sale_id.type_id.book_id})
        return res
