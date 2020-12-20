##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _create_delivery_line(self, carrier, price_unit):
        """
        So that delivery lines are not waiting invoice or delivery,
        if carrier price is:
        * zero: we add with qty 0 so nothing is needed to be invoiced or sent
        * not zero: we keep qty so it is set to be invoiced but we set it
        as delivered so you dont need to set it manually
        """
        sol = super()._create_delivery_line(carrier, price_unit)
        if not price_unit:
            sol.with_context(skip_validation='product_uom_qty').write({'product_uom_qty': 0.0})
        return sol
