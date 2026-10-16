from odoo import _, api, fields, models
from odoo.tools import float_compare


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    puede_cancelar_remanente = fields.Boolean(compute="_compute_puede_cancelar_remanente")

    @api.depends("state", "product_uom_qty", "qty_delivered", "product_id")
    def _compute_puede_cancelar_remanente(self):
        prec = self.env["decimal.precision"].precision_get("Product Unit")
        for line in self:
            line.puede_cancelar_remanente = bool(
                line.state == "sale" and line.product_id
                and line.qty_delivered_method == "stock_move"
                and float_compare(line.product_uom_qty, line.qty_delivered,
                                  precision_digits=prec) > 0)

    def button_cancel_remaining(self):
        """Deja la cantidad pedida en lo efectivamente entregado.

        ANTES (v19, con la capa):  product_uom_qty = qty_delivered + quantity_returned
        AHORA:                     product_uom_qty = qty_delivered

        Esa es toda la diferencia. Con una devolucion de por medio, la version vieja
        devolvia el mismo numero que ya habia (o sea, no hacia nada); esta lo baja.
        """
        a_destrabar = self.mapped("order_id").filtered(lambda o: o.locked)
        if a_destrabar:
            a_destrabar.with_context(tracking_disable=True).write({"locked": False})
        for rec in self.filtered("product_id"):
            anterior = rec.product_uom_qty
            rec.with_context(cancel_from_order=True).product_uom_qty = rec.qty_delivered
            if float_compare(anterior, rec.product_uom_qty,
                             precision_digits=self.env["decimal.precision"].precision_get("Product Unit")):
                rec.order_id.message_post(body=_(
                    "Cancelar remanente en «%(linea)s»: la cantidad pasó de %(antes)s a %(ahora)s.",
                    linea=rec.name or rec.product_id.display_name, antes=anterior, ahora=rec.product_uom_qty))
        if a_destrabar:
            a_destrabar.with_context(tracking_disable=True).write({"locked": True})
        return True


class SaleOrder(models.Model):
    _inherit = "sale.order"

    tiene_remanente = fields.Boolean(compute="_compute_tiene_remanente")

    @api.depends("order_line.puede_cancelar_remanente")
    def _compute_tiene_remanente(self):
        for order in self:
            order.tiene_remanente = any(l.puede_cancelar_remanente for l in order.order_line)

    def action_cancel_remaining(self):
        """Cancela el remanente de todas las lineas que tengan pendiente."""
        self.ensure_one()
        lineas = self.order_line.filtered("puede_cancelar_remanente")
        if lineas:
            lineas.button_cancel_remaining()
        return True
