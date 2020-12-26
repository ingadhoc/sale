##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def check_discount(self):
        # disable price_security constraint
        return True

    def check_discount_ok(self):
        self.ensure_one()
        # disable constrant
        if (self.user_has_groups('price_security.group_restrict_prices'
                                 ) and not self.product_can_modify_prices):
            # if something, then we have an error, not ok
            if self.env.user.check_discount(
                    self.discount,
                    self.order_id.pricelist_id.id,
                    so_line=self,
                    do_not_raise=True):
                return False
        return True
