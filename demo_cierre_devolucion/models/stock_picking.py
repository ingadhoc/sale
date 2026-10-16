from odoo import _, fields, models
from odoo.tools import float_compare


class StockPicking(models.Model):
    _inherit = "stock.picking"

    cierre_devolucion = fields.Selection(
        [("cerrado", "Se cerró el documento por lo entregado"),
         ("repone", "Queda pendiente para reponer")],
        string="Decisión sobre la devolución", copy=False, readonly=True,
        help="Qué se decidió hacer con el documento de origen al validar esta devolución.")

    def _devoluciones_que_dejan_remanente(self):
        """Lineas de venta/compra que quedarian con cantidad pendiente despues de
        validar esta devolucion. Se calcula ANTES del done, simulando el efecto."""
        prec = self.env["decimal.precision"].precision_get("Product Unit")
        res = []
        for picking in self:
            if not picking.return_id:
                continue
            for move in picking.move_ids:
                if move.state in ("done", "cancel") or not move.to_refund:
                    continue
                devuelve = move.product_uom_qty
                sol = move.sale_line_id if "sale_line_id" in move._fields else False
                pol = move.purchase_line_id if "purchase_line_id" in move._fields else False
                # Solo los movimientos que REDUCEN lo entregado/recibido. El picking de
                # cambio tambien es un "return" y hereda to_refund, pero su movimiento
                # SALE al cliente: ahi no hay nada que preguntar.
                vuelve_del_cliente = (move.location_id.usage == "customer"
                                      and move.location_dest_id.usage != "customer")
                vuelve_al_proveedor = move._is_purchase_return() if hasattr(move, "_is_purchase_return") else False
                if sol and not vuelve_del_cliente:
                    continue
                if pol and not vuelve_al_proveedor:
                    continue
                if sol:
                    qty = move.uom_id._compute_quantity(devuelve, sol.product_uom_id)
                    entregado = sol.qty_delivered - qty
                    pendiente = sol.product_uom_qty - entregado
                    previo = sol.product_uom_qty - sol.qty_delivered
                    if float_compare(pendiente, 0, precision_digits=prec) > 0:
                        res.append({
                            "picking": picking, "sale_line": sol, "purchase_line": False,
                            "producto": sol.product_id, "devuelve": qty,
                            "entregado": entregado, "pendiente": pendiente,
                            "previo": max(previo, 0.0),
                        })
                elif pol:
                    qty = move.uom_id._compute_quantity(devuelve, pol.uom_id)
                    recibido = pol.qty_received - qty
                    pendiente = pol.product_qty - recibido
                    previo = pol.product_qty - pol.qty_received
                    if float_compare(pendiente, 0, precision_digits=prec) > 0:
                        res.append({
                            "picking": picking, "sale_line": False, "purchase_line": pol,
                            "producto": pol.product_id, "devuelve": qty,
                            "entregado": recibido, "pendiente": pendiente,
                            "previo": max(previo, 0.0),
                        })
        return res

    def _pre_action_done_hook(self):
        """D3: antes de validar la devolucion, preguntar que hacer con el remanente.
        Usa el mismo mecanismo nativo que el wizard de backorder."""
        res = super()._pre_action_done_hook()
        if res is not True:
            return res
        if self.env.context.get("skip_cierre_devolucion"):
            return True
        datos = self._devoluciones_que_dejan_remanente()
        if not datos:
            return True
        wiz = self.env["return.close.confirmation"].create({
            "picking_ids": [(6, 0, self.ids)],
            "line_ids": [(0, 0, {
                "sale_line_id": d["sale_line"].id if d["sale_line"] else False,
                "purchase_line_id": d["purchase_line"].id if d["purchase_line"] else False,
                "product_id": d["producto"].id,
                "qty_returned": d["devuelve"],
                "qty_delivered_after": d["entregado"],
                "qty_pending": d["pendiente"],
                "qty_pending_before": d["previo"],
            }) for d in datos],
        })
        return {
            "name": _("Devolución: ¿qué hacemos con la venta?"),
            "type": "ir.actions.act_window",
            "res_model": "return.close.confirmation",
            "res_id": wiz.id,
            "view_mode": "form",
            "target": "new",
        }
