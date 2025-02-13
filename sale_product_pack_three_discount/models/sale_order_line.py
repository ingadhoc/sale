##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order.line"

    def _compute_discount(self):
        for pack_line in self.filtered("pack_parent_line_id"):
            context = self._context
            if context.get('pack_parent_line'):
                pack_line.discount1 = pack_line._get_pack_line_discount()
        res = super()._compute_discount()
        return res

    def expand_pack_line(self, write=False):
        return super(SaleOrder, self.with_context(pack_parent_line=True, recompute_prices=True)).expand_pack_line(write=write)
