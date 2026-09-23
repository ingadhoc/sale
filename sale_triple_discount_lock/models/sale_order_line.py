from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _inverse_discount(self):
        if self.env.context.get("sale_triple_discount_ux_skip_inverse"):
            return
        for rec in self:
            rec.update(
                {
                    "discount1": rec.discount,
                    "discount2": rec.discount2,
                    "discount3": rec.discount3,
                }
            )

    def _get_locked_discount1(self):
        self.ensure_one()
        discount_enabled = self.env["product.pricelist.item"]._is_discount_feature_enabled()
        if self.order_id.pricelist_id and discount_enabled and self.pricelist_item_id._show_discount():
            pricelist_price = self._get_pricelist_price()
            base_price = self._get_pricelist_price_before_discount()
            if base_price != 0:
                d = (base_price - pricelist_price) / base_price * 100
                if (d > 0 and base_price > 0) or (d < 0 and base_price < 0):
                    return d
        return 0.0

    def _compute_discounts(self):
        for rec in self:
            rec.update(
                {
                    "discount1": rec._get_locked_discount1(),
                    "discount2": rec.discount2,
                    "discount3": rec.discount3,
                }
            )
