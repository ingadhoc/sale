##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        return super(SaleOrder, self.with_context(confirming_order=True)).action_confirm()

    def _recompute_prices(self):
        super(SaleOrder, self.with_context(recompute_prices=True))._recompute_prices()
