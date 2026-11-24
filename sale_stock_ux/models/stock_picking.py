##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _prepare_return_move_default_values(self, move_id):
        vals = super()._prepare_return_move_default_values(move_id)
        # Returns and exchanges made in 20 are not the exchanges of the 19 wizard
        vals["is_exchange_move"] = False
        return vals
