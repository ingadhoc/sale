from odoo import fields, models


class ReturnCloseConfirmation(models.TransientModel):
    _name = "return.close.confirmation"
    _description = "Cerrar la venta al validar una devolucion"

    picking_ids = fields.Many2many("stock.picking")
    line_ids = fields.One2many("return.close.confirmation.line", "wizard_id")

    def _validar(self):
        pendientes = self.picking_ids.filtered(lambda p: p.state != "done")
        if not pendientes:
            return {"type": "ir.actions.act_window_close"}
        return pendientes.with_context(skip_cierre_devolucion=True).button_validate()

    def action_cerrar(self):
        """Valida la devolucion y despues baja la cantidad pedida a lo entregado."""
        self.ensure_one()
        lineas = self.line_ids
        res = self._validar()
        self.env.flush_all()
        self.env.invalidate_all()
        self.picking_ids.sudo().write({"cierre_devolucion": "cerrado"})
        # Reusa el boton de siempre: respeta sus validaciones y deja el mensaje
        # en el chatter. El boton ya trae la cuenta nueva (pedida = entregada).
        sol = lineas.mapped("sale_line_id")
        pol = lineas.mapped("purchase_line_id")
        if sol:
            sol.button_cancel_remaining()
        if pol:
            pol.button_cancel_remaining()
        self.env.flush_all()
        return res

    def action_dejar_pendiente(self):
        """Valida la devolucion sin tocar la venta: la mercaderia se va a reponer,
        asi que la cantidad pedida sigue siendo la correcta y SE PUEDE facturar."""
        self.ensure_one()
        res = self._validar()
        self.picking_ids.sudo().write({"cierre_devolucion": "repone"})
        return res


class ReturnCloseConfirmationLine(models.TransientModel):
    _name = "return.close.confirmation.line"
    _description = "Linea del cierre por devolucion"

    wizard_id = fields.Many2one("return.close.confirmation", ondelete="cascade")
    sale_line_id = fields.Many2one("sale.order.line")
    purchase_line_id = fields.Many2one("purchase.order.line")
    product_id = fields.Many2one("product.product", string="Producto")
    origen = fields.Char(compute="_compute_origen", string="Documento")
    qty_returned = fields.Float("Se devuelve", digits="Product Unit")
    qty_delivered_after = fields.Float("Queda entregado", digits="Product Unit")
    qty_pending = fields.Float("Quedaría pendiente", digits="Product Unit")
    qty_pending_before = fields.Float("Ya estaba pendiente", digits="Product Unit")
    ojo = fields.Boolean(compute="_compute_ojo")

    def _compute_origen(self):
        for l in self:
            l.origen = (l.sale_line_id.order_id.name if l.sale_line_id
                        else l.purchase_line_id.order_id.name if l.purchase_line_id else "")

    def _compute_ojo(self):
        """True si la linea YA tenia pendiente antes de la devolucion: cerrar le
        cancelaria al cliente mercaderia que si estaba esperando."""
        for l in self:
            l.ojo = l.qty_pending_before > 0
