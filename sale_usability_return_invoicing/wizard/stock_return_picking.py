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
        result = super(StockReturnPicking, self).default_get(fields)
        try:
            for line in result["product_return_moves"]:
                assert line[0] == 0
                # en realidad no nos importa si hay linea de venta o no ya que
                # también lo usamos en compras y queremos que en todo caso este
                # predeterminado el true. Ademas odoo en v11 no lo oculta o no
                # segun este campo y como tmb lo usamos para compras, en la
                # vista estamos sacando dicha funcionalidad entonces no sirve
                # para nada
                # line[2]["to_refund_so"] = line[2][
                #     "sale_order_id"] and True or False
                line[2]["to_refund_so"] = True
        except KeyError:
            pass
        return result
