##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    sale_id = fields.Many2one(
        related="sale_line_id.order_id",
    )
    is_exchange_move = fields.Boolean()

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        fields = super()._prepare_merge_moves_distinct_fields()
        fields.append("is_exchange_move")
        return fields

    @api.model_create_multi
    def create(self, vals_list):
        """La cantidad devuelta no deberia ser contada en los nuevos movimientos de
        entrega genuinos que se creen a partir de una orden de venta.
        Agregamos un HACK para que si esta instalado secondary unit sea recomputada en la creacion de
        movimientos de stock.

        Solo debe impactar en entregas genuinas: NO en los movimientos de
        devolucion (``origin_returned_move_id``) ni en los de devolucion para
        cambio (``is_exchange_move``). Esos ajustan la demanda por otra via y, si
        se les resta ``quantity_returned``, nacen con la demanda corrupta -- por
        ejemplo, una 2da devolucion o un cambio sobre una OV con una devolucion
        previa con reembolso quedaban con demanda = cantidad - quantity_returned.
        """
        for vals in vals_list:
            if (
                vals.get("sale_line_id")
                and not vals.get("is_exchange_move")
                and not vals.get("origin_returned_move_id")
            ):
                sale_line = self.env["sale.order.line"].browse(vals["sale_line_id"])
                # Para suscripciones NO restar quantity_returned: ya esta contemplado en
                # qty_delivered y en sale_order_line._create_procurements. Restarlo tambien aca
                # lo cuenta dos veces y deja el movimiento en cero (o negativo -> invierte el
                # picking a IN). Mismo criterio que _create_procurements.
                if not sale_line._check_is_recurring_invoice():
                    vals["product_uom_qty"] -= sale_line.quantity_returned
                if "secondary_uom_qty" in vals:
                    del vals["secondary_uom_qty"]

        return super().create(vals_list)

    def _get_new_picking_values(self):
        """return create values for new picking that will be linked with group
        of moves in self.
        """
        res = super()._get_new_picking_values()
        values = {}
        sale = self.mapped("sale_line_id.order_id")
        propagate_internal_notes = (
            self.env["ir.config_parameter"].sudo().get_param("sale.propagate_internal_notes") == "True"
        )
        propagate_note = self.env["ir.config_parameter"].sudo().get_param("sale.propagate_note") == "True"
        if propagate_internal_notes and sale.internal_notes:
            values["note"] = sale.internal_notes
        if propagate_note and sale.note:
            values["observations"] = sale.note
        if values:
            res.update(values)

        return res
