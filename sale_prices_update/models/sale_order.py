# -*- encoding: utf-8 -*-
from openerp import models, api


class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def update_prices(self):
        for line in self.order_line:
            price = self.pricelist_id.with_context(
                uom=line.product_uom.id,
                date=self.date_order).price_get(
                line.product_id.id,
                line.product_uom_qty or 1.0,
                self.partner_id.id
            )[self.pricelist_id.id]
            line.write({'price_unit': price})
        return True
