##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):

    _inherit = "sale.order"

    def _recompute_prices(self):
        if self.pricelist_id.discount_policy == 'with_discount':
            discount1 = {x: x.discount1 for x in self.order_line}
            super()._recompute_prices()
            for k, v in discount1.items():
                k.discount1 = v
        else:
            super()._recompute_prices()
