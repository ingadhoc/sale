from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    devolucion_sin_cerrar = fields.Float(
        string="Pendiente por devolución",
        compute="_compute_devolucion_sin_cerrar",
        digits="Product Unit",
        help="Unidades que quedaron pendientes de entregar porque hubo una devolución "
             "y no se cerró la cantidad pedida.",
    )

    @api.depends("product_uom_qty", "qty_delivered", "move_ids.state", "move_ids.to_refund")
    def _compute_devolucion_sin_cerrar(self):
        prec = self.env["decimal.precision"].precision_get("Product Unit")
        for line in self:
            pendiente = 0.0
            if line.state == "sale" and line.qty_delivered_method == "stock_move":
                # Solo lo que NADIE resolvio todavia. Una devolucion declarada como
                # "va a reponer" no cuenta: ahi la cantidad pedida sigue siendo correcta.
                sin_resolver = sum(
                    m.uom_id._compute_quantity(m.quantity, line.product_uom_id)
                    for m in line.move_ids
                    if m.state == "done" and m.to_refund
                    and m.location_id.usage == "customer"
                    and m.location_dest_id.usage != "customer"
                    and not m.picking_id.cierre_devolucion
                )
                falta = line.product_uom_qty - line.qty_delivered
                if float_compare(sin_resolver, 0, precision_digits=prec) > 0 and \
                   float_compare(falta, 0, precision_digits=prec) > 0:
                    pendiente = min(sin_resolver, falta)
            line.devolucion_sin_cerrar = pendiente


class SaleOrder(models.Model):
    _inherit = "sale.order"

    devolucion_sin_cerrar = fields.Boolean(compute="_compute_devolucion_sin_cerrar")

    @api.depends("order_line.devolucion_sin_cerrar")
    def _compute_devolucion_sin_cerrar(self):
        for order in self:
            order.devolucion_sin_cerrar = any(
                l.devolucion_sin_cerrar for l in order.order_line)

    def action_resolver_devolucion(self):
        """Salida desde el pedido: reabre la misma pregunta para las devoluciones
        que quedaron sin resolver. Asi la orden nunca queda trabada."""
        self.ensure_one()
        pickings = self.picking_ids.filtered(
            lambda p: p.return_id and p.state == "done" and not p.cierre_devolucion)
        datos = []
        prec = self.env["decimal.precision"].precision_get("Product Unit")
        from odoo.tools import float_compare as _fc
        for line in self.order_line:
            if not line.devolucion_sin_cerrar:
                continue
            devuelto = sum(
                m.uom_id._compute_quantity(m.quantity, line.product_uom_id)
                for m in line.move_ids
                if m.state == "done" and m.to_refund and m.location_id.usage == "customer")
            datos.append((0, 0, {
                "sale_line_id": line.id, "product_id": line.product_id.id,
                "qty_returned": devuelto,
                "qty_delivered_after": line.qty_delivered,
                "qty_pending": line.devolucion_sin_cerrar,
                "qty_pending_before": 0.0,
            }))
        if not datos:
            return {"type": "ir.actions.act_window_close"}
        wiz = self.env["return.close.confirmation"].create({
            "picking_ids": [(6, 0, pickings.ids)], "line_ids": datos})
        return {
            "name": _("Devolución sin resolver"),
            "type": "ir.actions.act_window",
            "res_model": "return.close.confirmation",
            "res_id": wiz.id, "view_mode": "form", "target": "new",
        }

    def _create_invoices(self, *args, **kwargs):
        """D2: red de seguridad. Si hay una devolución sin cerrar, no dejamos facturar
        sin que alguien lo mire: con política 'según lo pedido' se facturaría de más."""
        if not self.env.context.get("skip_chequeo_devolucion"):
            detalle = []
            for order in self:
                for line in order.order_line:
                    if line.devolucion_sin_cerrar and line.invoice_policy == "order":
                        detalle.append(_(
                            "  · %(orden)s — %(producto)s: pedidas %(ped)s, entregadas %(ent)s, "
                            "quedan %(pend)s sin entregar por una devolución",
                            orden=order.name, producto=line.product_id.display_name,
                            ped=line.product_uom_qty, ent=line.qty_delivered,
                            pend=line.devolucion_sin_cerrar))
            if detalle:
                raise UserError(_(
                    "Hay una devolución sin resolver y la facturación es «según lo pedido». "
                    "Si facturás así, le cobrás de más al cliente.\n\n%(detalle)s\n\n"
                    "Resolvelo con el botón «Resolver devolución» del pedido, eligiendo una "
                    "de las dos opciones:\n"
                    "  · Cerrar por lo entregado — la venta termina en lo que el cliente se quedó.\n"
                    "  · Queda pendiente para reponer — le vas a volver a entregar, y entonces "
                    "facturar lo pedido es correcto y no se frena más.",
                    detalle="\n".join(detalle)))
        return super()._create_invoices(*args, **kwargs)
