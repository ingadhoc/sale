##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _recompute_prices(self):
        super(SaleOrder, self.with_context(recompute_prices=True))._recompute_prices()
        lines_to_recompute = self._get_update_prices_lines()
        lines_to_recompute.with_context(recompute_prices=True)._compute_discounts()
