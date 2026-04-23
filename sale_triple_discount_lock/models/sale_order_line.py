from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_discount1_readonly = fields.Boolean(
        compute="_compute_is_discount1_readonly",
    )

    def _compute_is_discount1_readonly(self):
        readonly = (
            self.env["ir.config_parameter"].sudo().get_param("sale_triple_discount_ux.lock_discount1_readonly")
            == "True"
        )
        for rec in self:
            rec.is_discount1_readonly = readonly

    def _inverse_discount(self):
        if self.env.context.get("sale_triple_discount_ux_skip_inverse"):
            return
        if not self[:1].is_discount1_readonly:
            return super()._inverse_discount()
        for rec in self:
            rec.update(
                {
                    "discount1": rec.discount,
                    "discount2": rec.discount2,
                    "discount3": rec.discount3,
                }
            )

    def _compute_discounts(self):
        if not self[:1].is_discount1_readonly:
            return super()._compute_discounts()
        discount_enabled = self.env["product.pricelist.item"]._is_discount_feature_enabled()
        for rec in self:
            saved_d2 = rec.discount2
            saved_d3 = rec.discount3
            pricelist_discount = 0.0
            if rec.order_id.pricelist_id and discount_enabled and rec.pricelist_item_id._show_discount():
                pricelist_price = rec._get_pricelist_price()
                base_price = rec._get_pricelist_price_before_discount()
                if base_price != 0:
                    d = (base_price - pricelist_price) / base_price * 100
                    if (d > 0 and base_price > 0) or (d < 0 and base_price < 0):
                        pricelist_discount = d
            rec.update(
                {
                    "discount1": pricelist_discount,
                    "discount2": saved_d2,
                    "discount3": saved_d3,
                }
            )
