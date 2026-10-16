from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    qty_returned = fields.Float(
        string="Devuelto",
        compute="_compute_qty_returned",
        digits="Product Unit",
        help="Unidades devueltas al proveedor. Dato informativo: no participa de "
             "ningun calculo de facturacion ni de recepcion.",
    )

    @api.depends("move_ids.state", "move_ids.to_refund", "move_ids.quantity")
    def _compute_qty_returned(self):
        for line in self:
            qty = 0.0
            for move in line.move_ids.filtered(
                lambda m: m.state == "done" and m.to_refund and m._is_purchase_return()
            ):
                qty += move.uom_id._compute_quantity(move.quantity, line.uom_id)
            line.qty_returned = qty
