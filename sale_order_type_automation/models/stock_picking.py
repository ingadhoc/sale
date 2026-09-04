##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        """
        On picking confirmation we check if invoice should be created
        """
        res = super()._action_done()
        sale_orders = (
            self.filtered(lambda p: p.location_id._is_outgoing() or p.location_dest_id._is_outgoing())
            .sudo()
            .mapped("sale_id")
        )
        sale_orders.run_invoicing_atomation()
        return res
