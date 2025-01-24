##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order.line"

    def _compute_discount(self):
        pack_lines = self.filtered("pack_parent_line_id")
        super(SaleOrder, self - pack_lines)._compute_discount()
        for pack_line in pack_lines:
            pack_line.discount = pack_line._get_pack_line_discount()

    def _compute_discounts(self):
        pack_lines = self.filtered("pack_parent_line_id")
        super(SaleOrder, self - pack_lines)._compute_discounts()
        for line in pack_lines:
            line.discount1 = line.discount
            line.discount2 = 0.0
            line.discount3 = 0.0
