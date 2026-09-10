##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockForecasted(models.AbstractModel):
    _inherit = "stock.forecasted_product_product"

    def _prepare_report_line(
        self,
        quantity,
        move_out=None,
        move_in=None,
        replenishment_filled=True,
        product=False,
        reserved_move=False,
        in_transit=False,
        read=True,
    ):
        # sale_stock lee la OV del remito sin sudo: si el movimiento no tiene sale_line_id
        # el reporte revienta para un vendedor que no puede verla. Ticket 127167.
        if read and move_out and move_out.picking_id.sale_id:
            move_out.picking_id.sale_id.sudo().read(["amount_untaxed", "currency_id", "partner_id"])
        return super()._prepare_report_line(
            quantity, move_out, move_in, replenishment_filled, product, reserved_move, in_transit, read
        )
