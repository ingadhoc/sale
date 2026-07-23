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
        """HACK para que, si está instalado secondary unit, se recompute la
        unidad secundaria en la creación de movimientos de stock a partir de una
        orden de venta (borramos ``secondary_uom_qty`` para que se recalcule
        desde ``product_uom_qty``).

        La cantidad devuelta (``quantity_returned``) NO se resta acá: eso lo hace
        ``sale.order.line._create_procurements`` (que además excluye
        suscripciones vía ``_check_is_recurring_invoice``). Restarla también acá
        duplicaba el descuento y, al subir la cantidad pedida luego de una
        devolución total, dejaba la demanda en negativo -> Odoo invertía el
        movimiento y creaba una recepción (IN) en lugar de una entrega (OUT).
        Mismo criterio que 18.0, donde esta resta está deshabilitada.
        """
        for vals in vals_list:
            if vals.get("sale_line_id") and vals.get("secondary_uom_qty"):
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
