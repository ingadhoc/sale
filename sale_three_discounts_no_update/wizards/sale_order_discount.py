##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class SaleOrderDiscount(models.TransientModel):
    _inherit = "sale.order.discount"

    apply_discount1 = fields.Boolean("Apply Disc. 1", default=False)
    apply_discount2 = fields.Boolean("Apply Disc. 2", default=False)
    apply_discount3 = fields.Boolean("Apply Disc. 3", default=False)

    def action_apply_discount(self):
        lines = self.sale_order_id.order_line
        original = {line: (line.discount1, line.discount2, line.discount3) for line in lines}
        res = super().action_apply_discount()
        if self.discount_type == "sol_discount":
            for line in lines:
                d1, d2, d3 = original[line]
                if not self.apply_discount1:
                    line.discount1 = d1
                if not self.apply_discount2:
                    line.discount2 = d2
                if not self.apply_discount3:
                    line.discount3 = d3
                line.discount = line._calculate_total_discount()
        return res
