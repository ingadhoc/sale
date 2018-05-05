# -*- encoding: utf-8 -*-
from odoo import models, api


class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def update_prices(self):
        # for compatibility with product_pack module
        pack_installed = 'pack_parent_line_id' in self.order_line._fields
        for line in self.order_line:
            if pack_installed and line.pack_parent_line_id.\
                product_id.pack_price_type in [
                    'fixed_price', 'totalice_price']:
                price = 0.0
            else:
                price = self.pricelist_id.with_context(
                    uom=line.product_uom.id,
                    date=self.date_order).price_get(
                    line.product_id.id,
                    line.product_uom_qty or 1.0,
                    self.partner_id.id
                )[self.pricelist_id.id]
            line.write({'price_unit': price})
        return True
