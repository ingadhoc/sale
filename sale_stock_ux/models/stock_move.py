##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    sale_id = fields.Many2one(
        related="group_id.sale_id",
    )
    is_exchange_move = fields.Boolean()

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        fields = super()._prepare_merge_moves_distinct_fields()
        fields.append("is_exchange_move")
        return fields

    @api.model_create_multi
    def create(self, vals_list):
        """La cantidad devuelta no deberia ser contada en nuevos movimientos de stock
        que se creen a partir de una orden de venta.
        Agregamos un HACK para que si esta instalado secondary unit sea recomputada en la creacion de
        movimientos de stock.
        TODO: Solo deberia impactar en movimientos de salida (uno o mas pasos)
        TODO: Esto puede ser un problema si usamos unidades secundarias independientes pero por ahora
        lo dejamos asi porque calcular cuanto de una unidad secundaria corresponde a la cantidad devuelta
        es complejo.
        """
        for vals in vals_list:
            # # Nos aseguramos antes de restar que la rule_id es la primera de la ruta que estoy planificando
            # is_first_rule = self.env["stock.rule"].browse(vals.get("rule_id")).route_id.rule_ids[:1].id == vals.get(
            #     "rule_id"
            # )

            # if vals.get("sale_line_id") and not vals.get("origin_returned_move_id") and is_first_rule:
            #     sale_line_qty_ret = self.env["sale.order.line"].browse(vals["sale_line_id"]).quantity_returned
            #     vals["product_uom_qty"] -= sale_line_qty_ret
            if vals.get("sale_line_id") and vals.get("secondary_uom_qty"):
                del vals["secondary_uom_qty"]
        return super().create(vals_list)

    def _get_new_picking_values(self):
        """return create values for new picking that will be linked with group
        of moves in self.
        """
        res = super()._get_new_picking_values()
        values = {}
        sale = self.mapped("group_id.sale_id")
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
