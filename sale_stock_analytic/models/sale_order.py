##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _action_confirm(self):
        """ We need to ensure when the analytic account it was created after the moves creacion, 
        set for each move the analytic account for this sale.
        """
        res = super()._action_confirm()
        for order in self.filtered(lambda s: s.analytic_account_id and not all([x.analytic_account_id for x in s.order_line.mapped('move_ids')])):
            order.order_line.mapped('move_ids').write({'analytic_account_id': order.analytic_account_id.id})
        return res