from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    puede_cancelar_remanente = fields.Boolean(compute="_compute_puede_cancelar_remanente")

    @api.depends("state", "product_qty", "qty_received", "product_id")
    def _compute_puede_cancelar_remanente(self):
        prec = self.env["decimal.precision"].precision_get("Product Unit")
        for line in self:
            line.puede_cancelar_remanente = bool(
                line.order_id.state in ("purchase", "done") and line.product_id
                and float_compare(line.product_qty, line.qty_received,
                                  precision_digits=prec) > 0)

    def button_cancel_remaining(self):
        """Deja la cantidad pedida en lo efectivamente recibido.
        ANTES: product_qty = qty_received + qty_returned   AHORA: product_qty = qty_received"""
        prec = self.env["decimal.precision"].precision_get("Product Unit")
        a_destrabar = self.mapped("order_id").filtered(lambda o: o.state == "done")
        if a_destrabar:
            a_destrabar.with_context(tracking_disable=True).write({"state": "purchase"})
        for rec in self:
            if float_compare(rec.qty_invoiced, rec.qty_received, precision_digits=prec) > 0:
                raise UserError(_(
                    "No se puede cancelar el remanente de «%(linea)s»: hay más facturado (%(fact)s) "
                    "que recibido (%(rec)s). Corregí la factura o pedí la nota de crédito primero.",
                    linea=rec.name or rec.product_id.display_name, fact=rec.qty_invoiced, rec=rec.qty_received))
            anterior = rec.product_qty
            rec.with_context(cancel_from_order=True).product_qty = rec.qty_received
            if float_compare(anterior, rec.product_qty, precision_digits=prec):
                rec.order_id.message_post(body=_(
                    "Cancelar remanente en «%(linea)s»: la cantidad pasó de %(antes)s a %(ahora)s.",
                    linea=rec.name or rec.product_id.display_name, antes=anterior, ahora=rec.product_qty))
        if a_destrabar:
            a_destrabar.with_context(tracking_disable=True).write({"state": "done"})
        return True


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    tiene_remanente = fields.Boolean(compute="_compute_tiene_remanente")

    @api.depends("order_line.puede_cancelar_remanente")
    def _compute_tiene_remanente(self):
        for order in self:
            order.tiene_remanente = any(l.puede_cancelar_remanente for l in order.order_line)

    def action_cancel_remaining(self):
        self.ensure_one()
        lineas = self.order_line.filtered("puede_cancelar_remanente")
        if lineas:
            lineas.button_cancel_remaining()
        return True
