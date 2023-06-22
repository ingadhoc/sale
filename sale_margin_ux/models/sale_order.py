##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_update_prices(self):
        super().action_update_prices()
        self.order_line._compute_purchase_price()
        return True
