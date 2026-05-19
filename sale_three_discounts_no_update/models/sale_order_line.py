from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _compute_discount(self):
        """Preserve manual 3-discount values during standard recomputations."""
        cache = {line: (line.discount1, line.discount2, line.discount3) for line in self}
        super()._compute_discount()
        for line in self:
            discount_1, discount_2, discount_3 = cache[line]
            if discount_1 or discount_2 or discount_3:
                line.discount1 = discount_1
                line.discount2 = discount_2
                line.discount3 = discount_3
                line.discount = line._calculate_total_discount()

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            if line.discount1 or line.discount2 or line.discount3:
                line.discount = line._calculate_total_discount()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if any(field in vals for field in ["discount1", "discount2", "discount3"]):
            for line in self:
                line.discount = line._calculate_total_discount()
        return res
