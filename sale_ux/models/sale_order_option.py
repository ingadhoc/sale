##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrderOption(models.Model):
    _inherit = 'sale.order.option'

    def _restore_order_line(self, method):
        if self._context.get('onchange_pricelist_id'):
            order_line = self.order_id.order_line
            method()
            self.order_id.order_line = order_line
        else:
            method()

    def _compute_price_unit(self):
        self._restore_order_line(super(SaleOrderOption, self)._compute_price_unit)

    def _compute_discount(self):
        self._restore_order_line(super(SaleOrderOption, self)._compute_discount)
