from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    devolucion_sin_cerrar = fields.Float(
        string="Pendiente por devolución",
        compute="_compute_devolucion_sin_cerrar",
        digits="Product Unit",
    )

    @api.depends("product_qty", "qty_received", "move_ids.state", "move_ids.to_refund")
    def _compute_devolucion_sin_cerrar(self):
        prec = self.env["decimal.precision"].precision_get("Product Unit")
        for line in self:
            pendiente = 0.0
            if line.order_id.state in ("purchase", "done"):
                sin_resolver = sum(
                    m.uom_id._compute_quantity(m.quantity, line.uom_id)
                    for m in line.move_ids
                    if m.state == "done" and m.to_refund and m._is_purchase_return()
                    and not m.picking_id.cierre_devolucion
                )
                falta = line.product_qty - line.qty_received
                if float_compare(sin_resolver, 0, precision_digits=prec) > 0 and \
                   float_compare(falta, 0, precision_digits=prec) > 0:
                    pendiente = min(sin_resolver, falta)
            line.devolucion_sin_cerrar = pendiente


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def action_create_invoice(self, attachment_ids=False):
        if not self.env.context.get("skip_chequeo_devolucion"):
            detalle = []
            for order in self:
                for line in order.order_line:
                    if line.devolucion_sin_cerrar and line.product_id.purchase_method == "purchase":
                        detalle.append(_(
                            "  · %(orden)s — %(producto)s: pedidas %(ped)s, recibidas %(rec)s, "
                            "quedan %(pend)s sin recibir por una devolución",
                            orden=order.name, producto=line.product_id.display_name,
                            ped=line.product_qty, rec=line.qty_received,
                            pend=line.devolucion_sin_cerrar))
            if detalle:
                raise UserError(_(
                    "Hay devoluciones al proveedor sin cerrar y el control es «según lo pedido»: "
                    "si facturás así, pagás de más.\n\n%(detalle)s\n\n"
                    "Cerrá la cantidad pedida en esas líneas y volvé a facturar.",
                    detalle="\n".join(detalle)))
        return super().action_create_invoice(attachment_ids=attachment_ids)
