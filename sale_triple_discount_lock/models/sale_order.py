from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _recompute_prices(self):
        # super() calls lines._compute_discount() as a plain method call, not
        # via ORM recomputation, so it is unprotected: every write to 'discount'
        # inside OCA's override triggers _inverse_discount, which ends up setting
        # discount1 = combined_triple_discount instead of the pricelist discount.
        # We save d2/d3 before super() and restore them (with the correct d1) after.
        saved = {line.id: (line.discount2, line.discount3) for line in self.order_line}

        super()._recompute_prices()

        discount_enabled = self.env["product.pricelist.item"]._is_discount_feature_enabled()
        for line in self.order_line:
            d2, d3 = saved[line.id]
            pricelist_discount = 0.0
            if line.order_id.pricelist_id and discount_enabled and line.pricelist_item_id._show_discount():
                pricelist_price = line._get_pricelist_price()
                base_price = line._get_pricelist_price_before_discount()
                if base_price != 0:
                    d = (base_price - pricelist_price) / base_price * 100
                    if (d > 0 and base_price > 0) or (d < 0 and base_price < 0):
                        pricelist_discount = d
            line.with_context(sale_triple_discount_ux_skip_inverse=True).write(
                {"discount1": pricelist_discount, "discount2": d2, "discount3": d3}
            )
