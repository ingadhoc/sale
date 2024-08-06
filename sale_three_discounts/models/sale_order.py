##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):

    _inherit = "sale.order"

    def _recompute_prices(self):
        if self.pricelist_id.discount_policy == 'with_discount':
            discounts = {x: (x.discount1, x.discount2, x.discount3) for x in self.order_line}
            super()._recompute_prices()
            for line, (disc1, disc2, disc3) in discounts.items():
                line.discount1 = disc1
                line.discount2 = disc2
                line.discount3 = disc3
        else:
            super()._recompute_prices()
