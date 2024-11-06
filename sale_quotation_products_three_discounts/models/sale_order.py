##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def add_products(self, product_ids, qty):
        super().add_products(product_ids, qty)
        last_line = self.order_line.sorted(key=lambda l: l.sequence, reverse=True)[:1]
        if last_line:
            last_line._onchange_discounts()
