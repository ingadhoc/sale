# Copyright 2026 ADHOC SA (http://www.adhoc.com.ar)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_pack_sale_discount(self):
        """The sale_discount the parent pack gives this component, 0 if there is none."""
        self.ensure_one()
        if self.pack_parent_line_id.pack_component_price != "detailed":
            return 0.0
        pack_line = self.pack_parent_line_id.product_id.pack_line_ids.filtered(
            lambda line, s=self: line.product_id == s.product_id
        )[:1]
        return pack_line.sale_discount

    @api.depends("product_id", "product_uom_id", "product_uom_qty", "pack_parent_line_id")
    def _compute_discount1(self):
        # sale_triple_discount owns 'discount' as a pure function of discount1/2/3,
        # so what sale_product_pack writes there is wiped. Where the pricelist can
        # give a discount super() already drags the pack one along; where it cannot
        # it leaves the old value, and the component ends up with no discount.
        res = super()._compute_discount1()
        discount_enabled = self.env["product.pricelist.item"]._is_discount_feature_enabled()
        skipped_by_super = self.filtered(
            lambda line: line.pack_parent_line_id and not (line.order_id.pricelist_id and discount_enabled)
        )
        for line in skipped_by_super:
            line.discount1 = line._get_pack_sale_discount()
        return res
