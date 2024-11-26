##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _recompute_prices(self):
        super(SaleOrder, self.with_context(recompute_prices=True))._recompute_prices()

    @api.onchange('pricelist_id')
    def _onchange_pricelist(self):
        self.order_line.write({
            'discount1': 0,
            'discount2': 0,
            'discount3': 0
        })
        self._recompute_prices()
