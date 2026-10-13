from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    quantity_returned = fields.Float(
        string="Devuelto",
        compute="_compute_quantity_returned",
        digits="Product Unit",
        help="Unidades que el cliente devolvio. Dato informativo: no participa de "
             "ningun calculo de facturacion ni de entrega.",
    )

    @api.depends("move_ids.state", "move_ids.to_refund", "move_ids.quantity")
    def _compute_quantity_returned(self):
        for line in self:
            qty = 0.0
            if line.qty_delivered_method == "stock_move":
                returns = line.move_ids.filtered(
                    lambda m: m.state == "done"
                    and m.to_refund
                    and m.location_id.usage == "customer"
                    and m.location_dest_id.usage != "customer"
                )
                for move in returns:
                    qty += move.uom_id._compute_quantity(move.quantity, line.product_uom_id)
            line.quantity_returned = qty
