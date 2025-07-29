##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _compute_purchase_price(self):
        super()._compute_purchase_price()
        for line in self.filtered(
            lambda l: l.is_gathering
            and l.order_id
            and l.order_id.coef
            and l.product_id
            and isinstance(l.id, models.NewId)
        ):
            product_cost = line.product_id.uom_id._compute_price(
                line.product_id.standard_price,
                line.product_uom,
            )
            base_price = line._convert_to_sol_currency(product_cost, line.product_id.cost_currency_id)
            line.purchase_price = base_price / line.order_id.coef
