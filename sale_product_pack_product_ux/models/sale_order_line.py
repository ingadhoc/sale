##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_pack_descendant_lines(self):
        self.ensure_one()
        lines = self.env["sale.order.line"]
        for child in self.pack_child_line_ids:
            lines |= child | child._get_pack_descendant_lines()
        return lines

    def _get_whole_pack_discounted_price(self):
        self.ensure_one()
        price = self._get_discounted_price()
        if not self.product_uom_qty:
            return price
        for line in self._get_pack_descendant_lines():
            price += line._get_discounted_price() * line.product_uom_qty / self.product_uom_qty
        return price

    def _get_product_catalog_lines_data(self, **kwargs):
        if len(self) > 1:
            records = self.with_context(whole_pack_price=True)
            return super(SaleOrderLine, records)._get_product_catalog_lines_data(**kwargs)
        res = super()._get_product_catalog_lines_data(**kwargs)
        if len(self) == 1 and self.pack_child_line_ids:
            res["price"] = self._get_whole_pack_discounted_price()
        return res
