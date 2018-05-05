# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from openerp import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def update_prices(self):
        super(SaleOrder, self).update_prices()
        for line in self.order_line:
            purchase_price = line._compute_margin(
                self, line.product_id, line.product_uom)
            line.write({'purchase_price': purchase_price})
        return True
