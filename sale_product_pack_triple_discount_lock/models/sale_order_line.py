# Copyright 2026 ADHOC SA (http://www.adhoc.com.ar)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_locked_discount1(self):
        d1 = super()._get_locked_discount1()
        if self.pack_parent_line_id.pack_component_price == "detailed":
            for pack_line in self.pack_parent_line_id.product_id.pack_line_ids:
                if pack_line.product_id == self.product_id:
                    return 100.0 - (100.0 - d1) * (100.0 - pack_line.sale_discount) / 100.0
        return d1

    def _compute_discount(self):
        res = super()._compute_discount()
        for line in self.filtered("pack_parent_line_id"):
            line.discount = line._get_final_discount()
        return res
