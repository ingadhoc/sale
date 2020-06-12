##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def update_prices(self):
        super().update_prices()
        for line in self.order_line:
            purchase_price = line._compute_margin(
                self, line.product_id, line.product_uom)
            line.purchase_price = purchase_price
        return True
