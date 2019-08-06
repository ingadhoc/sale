##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


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
