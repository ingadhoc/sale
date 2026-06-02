##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class SaleOrderDiscount(models.TransientModel):
    _inherit = "sale.order.discount"

    discount2 = fields.Float("Discount 2 (%)", default=0.0)
    discount3 = fields.Float("Discount 3 (%)", default=0.0)
    apply_discount2 = fields.Boolean("Apply Disc. 2", default=False)
    apply_discount3 = fields.Boolean("Apply Disc. 3", default=False)
    total_discount = fields.Float(compute="_compute_total_discount")

    @api.depends("discount2", "apply_discount2", "discount3", "apply_discount3")
    def _compute_total_discount(self):
        for rec in self:
            d2 = rec.discount2 if rec.apply_discount2 else 0.0
            d3 = rec.discount3 if rec.apply_discount3 else 0.0
            rec.total_discount = 1.0 - (1.0 - d2) * (1.0 - d3)

    def action_apply_discount(self):
        if self.discount_type != "sol_discount":
            return super().action_apply_discount()

        lines = self.sale_order_id.order_line
        original = {line: (line.discount1, line.discount2, line.discount3) for line in lines}

        res = super().action_apply_discount()

        for line in lines:
            d1, d2, d3 = original[line]
            line.with_context(sale_triple_discount_ux_skip_inverse=True).write(
                {
                    "discount1": d1,
                    "discount2": self.discount2 * 100 if self.apply_discount2 else d2,
                    "discount3": self.discount3 * 100 if self.apply_discount3 else d3,
                }
            )

        return res
