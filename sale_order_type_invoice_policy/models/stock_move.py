##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_assign(self):
        """
        For the cron call check if the moves needs to be reserved or not depends of the policy in the sale order type.
        """
        prepaid_unpaid = self.sudo().filtered(lambda x: x.picking_id.sale_id.type_id.invoice_policy ==
            'prepaid' and not x.picking_id._check_sale_paid())
        if prepaid_unpaid:
            self -= prepaid_unpaid
            # do not call super if not self because it raise an error
            if not self:
                return True
        return super()._action_assign()
