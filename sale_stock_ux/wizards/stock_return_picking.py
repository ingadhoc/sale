##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    @api.model
    def default_get(self, fields):
        """Get sale order for lines."""
        result = super().default_get(fields)
        try:
            for line in result["product_return_moves"]:
                assert line[0] == 0
                # en realidad no nos importa si hay linea de venta o no ya que
                # también lo usamos en compras y queremos que en todo caso este
                line[2]["to_refund"] = True
        except KeyError:
            pass
        return result

    def action_create_exchanges(self):
        action = super().action_create_exchanges()
        self.picking_id.return_ids.move_ids.write({"to_redeliver": True})
        return action
