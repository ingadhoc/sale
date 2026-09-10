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

        for line in self.order_line:
            d2, d3 = saved[line.id]
            line.with_context(sale_triple_discount_ux_skip_inverse=True).write(
                {"discount1": line._get_locked_discount1(), "discount2": d2, "discount3": d3}
            )
