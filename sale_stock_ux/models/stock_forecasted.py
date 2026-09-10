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
        """`sale_stock` lee la OV del remito sin sudo y el pronosticado revienta si es de otro vendedor.

        Pasa con cualquier movimiento saliente sin `sale_line_id` cuyo remito sí
        tenga OV (una línea agregada a mano al remito, por ejemplo): ahí el
        `sudo()` de `_get_source_document` no llega a traer la OV a la caché y
        `sale_stock` la lee con el usuario. La traemos nosotros con sudo, que es
        lo que el reporte ya hace con el resto de los datos de la OV. Ticket 127167.
        """
        if read and move_out and move_out.picking_id.sale_id:
            move_out.picking_id.sale_id.sudo().read(["amount_untaxed", "currency_id", "partner_id"])
        return super()._prepare_report_line(
            quantity, move_out, move_in, replenishment_filled, product, reserved_move, in_transit, read
        )
