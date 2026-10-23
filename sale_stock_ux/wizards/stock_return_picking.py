##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    def action_create_exchanges(self):
        # An exchange restocks the same products: the SO/PO quantities must not change
        self.product_return_moves.to_refund = False
        return super(StockReturnPicking, self.with_context(is_exchange_move=True)).action_create_exchanges()


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    def _prepare_move_default_values(self, new_picking):
        vals = super()._prepare_move_default_values(new_picking)
        if self.env.context.get("is_exchange_move"):
            vals["is_exchange_move"] = True
        return vals

    def _prepare_picking_default_values_based_on(self, picking):
        vals = super()._prepare_picking_default_values_based_on(picking)
        if self.env.context.get("is_exchange_move"):
            vals["is_exchange_move"] = True
        return vals
