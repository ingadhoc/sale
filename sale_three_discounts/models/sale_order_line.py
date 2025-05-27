##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discount1 = fields.Float(
        "Disc. 1 (%)", digits="Discount", compute="_compute_discount", precompute=True, store=True, readonly=False
    )
    discount2 = fields.Float(
        "Disc. 2 (%)", digits="Discount", compute="_compute_discount", precompute=True, store=True, readonly=False
    )
    discount3 = fields.Float(
        "Disc. 3 (%)", digits="Discount", compute="_compute_discount", precompute=True, store=True, readonly=False
    )
    discount = fields.Float(readonly=True)

    @api.constrains("discount1", "discount2", "discount3")
    def check_discount_validity(self):
        for rec in self:
            error = []
            if rec.discount1 > 100:
                error.append("Discount 1")
            if rec.discount2 > 100:
                error.append("Discount 2")
            if rec.discount3 > 100:
                error.append("Discount 3")
            if error:
                raise ValidationError(_(",".join(error) + " must be less or equal than 100"))

    def _compute_discount(self):
        # we do not want override discounts if the pricelist is configured to include the discount in the price.
        lines_show_discount = self.filtered(lambda x: x.order_id.pricelist_id and x.pricelist_item_id._show_discount())
        super(SaleOrderLine, lines_show_discount)._compute_discount()
        if self.env.context.get("recompute_prices") or lines_show_discount:
            for line in self:
                line.discount1 = line.discount
                line.discount2 = 0.0
                line.discount3 = 0.0

    @api.onchange("discount1", "discount2", "discount3")
    def _onchange_discounts(self):
        for line in self:
            discount_factor = 1.0
            for discount in [line.discount1, line.discount2, line.discount3]:
                discount_factor *= (100.0 - discount) / 100.0
            line.discount = 100.0 - (discount_factor * 100.0)

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        res.update({"discount1": self.discount1, "discount2": self.discount2, "discount3": self.discount3})
        return res
