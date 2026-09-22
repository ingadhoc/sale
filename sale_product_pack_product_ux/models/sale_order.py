##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_product_catalog_order_data(self, products, **kwargs):
        return super()._get_product_catalog_order_data(products.with_context(whole_pack_price=True), **kwargs)

    def _update_order_line_info(self, product_id, quantity, **kwargs):
        res = super()._update_order_line_info(product_id, quantity, **kwargs)
        product = self.env["product.product"].browse(product_id).with_context(whole_pack_price=True)
        if not product._is_pack_to_be_handled():
            return res
        line = self.order_line.filtered(lambda line: line.product_id.id == product_id and not line.pack_parent_line_id)
        if line:
            return line[0]._get_whole_pack_discounted_price()
        return self.pricelist_id._get_product_price(
            product=product,
            quantity=1.0,
            currency=self.currency_id,
            date=self.date_order,
            **kwargs,
        )
