##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_stock_move_values(
            self, product_id, product_qty, product_uom, location_id, name,
            origin, values, group_id):
        result = super()._get_stock_move_values(
            product_id, product_qty, product_uom, location_id, name,
            origin, values, group_id)
        sale_line_id = values.get('sale_line_id', False)
        if sale_line_id:
            result['analytic_tag_ids'] = [
                (6, 0, self.env[
                    'sale.order.line'].browse(
                        sale_line_id).analytic_tag_ids.ids)]
        return result
