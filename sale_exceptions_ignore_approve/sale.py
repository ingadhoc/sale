# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def _popup_exceptions(self):
        action = self.env.ref('sale_exception.action_sale_exception_confirm')
        action = action.read()[0]
        ctx = self._context.copy()
        ctx.update({
            'active_id': self.ids[0],
            'active_ids': self.ids
        })
        action.update({
            'context': ctx
        })
        return action
