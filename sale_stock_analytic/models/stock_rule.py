##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_stock_move_values(
            self, product_id, product_qty, product_uom, location_id, name,
            origin, company_id, values):
        result = super()._get_stock_move_values(
            product_id, product_qty, product_uom, location_id, name,
            origin, company_id, values)
        sol_id = values.get('sale_line_id', False)
        if sol_id:
            sol = self.env["sale.order.line"].browse(sol_id)
            analytic_account = sol.order_id.analytic_account_id
            analytic_tags = sol.analytic_tag_ids
            if analytic_tags:
                result['analytic_tag_ids'] = [(6, 0, analytic_tags.ids)]
            if analytic_account:
                result['analytic_account_id'] = analytic_account.id
        return result
