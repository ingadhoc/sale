from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def write(self, values):
        orders_to_automate = self.env["sale.order"]
        eligible_lines = self.env["sale.order.line"]
        old_qty = {}
        if "product_uom_qty" in values:
            eligible_lines = self.filtered(
                lambda l: l.order_id.is_gathering and l.order_id.state == "sale" and l.initial_qty_gathered > 0
            )
            old_qty = {l.id: l.product_uom_qty for l in eligible_lines}
        res = super().write(values)
        orders_to_automate = eligible_lines.filtered(lambda l: l.product_uom_qty > old_qty.get(l.id, 0)).mapped(
            "order_id"
        )
        if orders_to_automate:
            orders_picking_automation = orders_to_automate.filtered(lambda o: o.type_id.picking_atomation != "none")
            orders_picking_automation.run_picking_automation()
            (orders_to_automate - orders_picking_automation).run_invoicing_atomation()

        return res

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        orders_to_automate = lines.filtered(
            lambda l: l.order_id.is_gathering and l.order_id.state == "sale" and l.product_uom_qty > 0
        ).mapped("order_id")
        if orders_to_automate:
            orders_picking_automation = orders_to_automate.filtered(lambda o: o.type_id.picking_atomation != "none")
            orders_picking_automation.run_picking_automation()
            (orders_to_automate - orders_picking_automation).run_invoicing_atomation()
        return lines
