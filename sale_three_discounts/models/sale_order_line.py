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
        # we do not want override discounts if the pricelist is configured to include the discount in the price
        # in SO confirmed.
        lines = self.filtered(
            lambda x: x.order_id.state == "sale"
            and not (x.order_id.pricelist_id and x.pricelist_item_id._show_discount())
        )
        lines_to_update = self - lines
        super(SaleOrderLine, lines_to_update)._compute_discount()

        if self.env.context.get("recompute_prices") or lines_to_update:
            for line in self:
                if line.order_id.state != "sale":
                    line.discount1 = line.discount
                    line.discount2 = 0.0
                    line.discount3 = 0.0

        # Recalcular descuento total para todos
        for line in self:
            if line.discount1 or line.discount2 or line.discount3:
                line.discount = line._calculate_total_discount()

    def _calculate_total_discount(self):
        """Calcula el descuento total a partir de discount1, discount2 y discount3"""
        self.ensure_one()
        discount_factor = 1.0
        for discount in [self.discount1, self.discount2, self.discount3]:
            discount_factor *= (100.0 - discount) / 100.0
        return 100.0 - (discount_factor * 100.0)

    @api.onchange("discount1", "discount2", "discount3")
    def _onchange_discounts(self):
        for line in self:
            line.discount = line._calculate_total_discount()

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        res.update({"discount1": self.discount1, "discount2": self.discount2, "discount3": self.discount3})
        return res
