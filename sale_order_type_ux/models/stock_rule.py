##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _get_sale_type_picking_type(self, sale_lines):
        """Operation type of the sale order type, only for the step that goes to the customer."""
        if self.picking_type_id.code != "outgoing":
            return self.env["stock.picking.type"]
        return sale_lines.order_id.type_id.picking_type_id[:1]

    def _get_stock_move_values(
        self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values
    ):
        res = super()._get_stock_move_values(
            product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values
        )
        sale_lines = self.env["sale.order.line"].browse(values.get("sale_line_id"))
        picking_type = self._get_sale_type_picking_type(sale_lines)
        if picking_type:
            res["picking_type_id"] = picking_type.id
        return res

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        """With deliveries in two or three steps the last one is created by a push rule."""
        res = super()._push_prepare_move_copy_values(move_to_copy, new_date)
        picking_type = self._get_sale_type_picking_type(move_to_copy.sale_line_id)
        if picking_type:
            res["picking_type_id"] = picking_type.id
        return res
