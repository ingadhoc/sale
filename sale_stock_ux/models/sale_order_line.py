##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.tools.float_utils import float_compare, float_is_zero


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    all_qty_delivered = fields.Float(
        string="All Delivered",
        compute="_compute_all_qty_delivered",
        help="Everything delivered without discounting the returns",
        digits="Product Unit of Measure",
    )

    quantity_returned = fields.Float(
        string="Returned Quantity",
        compute="_compute_quantity_returned",
        copy=False,
        digits="Product Unit of Measure",
    )

    delivery_status = fields.Selection(
        [
            ("no", "Nothing to deliver"),
            ("to deliver", "To Deliver"),
            ("full", "Fully Delivered"),
        ],
        compute="_compute_delivery_status",
        store=True,
        readonly=True,
        copy=False,
        default="no",
    )
    total_reserved_quantity = fields.Float(compute="_compute_total_reserved_quantity")
    stock_by_location = fields.Text(compute="_compute_stock_by_location")

    def _check_is_recurring_invoice(self):
        self.ensure_one()
        if (
            self.order_id._fields.get("is_subscription")
            and self.order_id.is_subscription
            and self._fields.get("recurring_invoice")
            and self.recurring_invoice
        ):
            return self.recurring_invoice
        return False

    def _create_procurements(self, product_qty, procurement_uom, origin, values):
        self.ensure_one()
        # cancelar remanente seta la cantidad como entregada menos devuelta
        # asi que no deberia restar en ese caso
        # Para suscripciones: NO restar quantity_returned (ya está en qty_delivered)
        if not self._check_is_recurring_invoice():
            product_qty = product_qty - self.quantity_returned
        return super()._create_procurements(product_qty, procurement_uom, origin, values)

    @api.depends("product_id", "product_uom_qty")
    def _compute_total_reserved_quantity(self):
        # Batched: one grouped query per distinct warehouse stock location instead
        # of a stock.quant search per line (avoids an N+1 on the order form load).
        self.total_reserved_quantity = 0.0
        lines = self.filtered(lambda line: line.product_id and line.order_id.warehouse_id.lot_stock_id)
        for root_location, root_lines in lines.grouped(lambda line: line.order_id.warehouse_id.lot_stock_id).items():
            reserved_by_product = {
                product.id: reserved
                for product, reserved in self.env["stock.quant"]._read_group(
                    domain=[
                        ("product_id", "in", root_lines.product_id.ids),
                        ("location_id", "child_of", root_location.id),
                    ],
                    groupby=["product_id"],
                    aggregates=["reserved_quantity:sum"],
                )
            }
            for line in root_lines:
                line.total_reserved_quantity = reserved_by_product.get(line.product_id.id, 0.0)

    @api.depends("qty_delivered", "quantity_returned")
    def _compute_all_qty_delivered(self):
        for rec in self:
            rec.all_qty_delivered = rec.qty_delivered + rec.quantity_returned

    def _get_qty_procurement(self, previous_product_uom_qty=False):
        qty = super()._get_qty_procurement(previous_product_uom_qty=previous_product_uom_qty)
        outgoing_moves, incoming_moves = self._get_outgoing_incoming_moves(strict=False)
        for move in outgoing_moves.filtered(lambda m: m.is_exchange_move):
            qty_to_compute = move.quantity if move.state == "done" else move.product_uom_qty
            qty -= move.product_uom._compute_quantity(qty_to_compute, self.product_uom, rounding_method="HALF-UP")
        for move in incoming_moves.filtered(lambda m: m.is_exchange_move):
            qty_to_compute = move.quantity if move.state == "done" else move.product_uom_qty
            qty += move.product_uom._compute_quantity(qty_to_compute, self.product_uom, rounding_method="HALF-UP")
        return qty

    @api.depends()
    def _compute_qty_delivered(self):
        super()._compute_qty_delivered()
        for line in self:
            if line.qty_delivered_method == "stock_move":
                outgoing_moves, incoming_moves = line._get_outgoing_incoming_moves()
                for move in outgoing_moves.filtered(lambda m: m.is_exchange_move and m.state == "done"):
                    line.qty_delivered -= move.product_uom._compute_quantity(
                        move.quantity, line.product_uom, rounding_method="HALF-UP"
                    )
                for move in incoming_moves.filtered(lambda m: m.is_exchange_move and m.state == "done"):
                    line.qty_delivered += move.product_uom._compute_quantity(
                        move.quantity, line.product_uom, rounding_method="HALF-UP"
                    )

    @api.depends("order_id.state", "qty_delivered", "product_uom_qty", "order_id.force_delivery_status")
    def _compute_delivery_status(self):
        precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        for line in self:
            if line.state not in ("sale", "done"):
                line.delivery_status = "no"
                continue

            if line.order_id.force_delivery_status:
                line.delivery_status = line.order_id.force_delivery_status
                continue

            if float_compare(line.all_qty_delivered, line.product_uom_qty, precision_digits=precision) == -1:
                delivery_status = "to deliver"
            elif float_compare(line.all_qty_delivered, line.product_uom_qty, precision_digits=precision) >= 0:
                delivery_status = "full"
            else:
                delivery_status = "no"
            line.delivery_status = delivery_status

    def button_cancel_remaining(self):
        # la cancelación de kits no está bien resuelta ya que odoo solo computa
        # la cantidad entregada cuando todo el kit se entregó. Cuestión que,
        # por ahora, desactivamos la cancelación de kits

        # Manejar órdenes bloqueadas: desbloquear temporalmente sin tracking
        orders = self.mapped("order_id")
        orders_to_relock = orders.filtered(lambda o: o.locked)
        if orders_to_relock:
            orders_to_relock.with_context(tracking_disable=True).write({"locked": False})
        try:
            # Resetear printed=False en pickings abiertos de la orden para poder
            # cancelar sus moves cuando el tipo de operación restringe cancelar impresos.
            pickings_to_reset = orders.mapped("picking_ids").filtered(
                lambda p: p.state not in ("done", "cancel") and p.printed
            )
            if pickings_to_reset:
                pickings_to_reset.write({"printed": False})

            pack_enable = "pack_ok" in self.env["product.template"]._fields
            for rec in self.filtered("product_id"):
                # For product pack compatibility to cancel all of componept in case the product parent is cancel
                if pack_enable and rec.product_id.pack_ok and rec.pack_type == "detailed" and rec.pack_child_line_ids:
                    rec.pack_child_line_ids.with_context(cancel_from_order=True).button_cancel_remaining()

                old_product_uom_qty = rec.product_uom_qty

                # Al final permitimos cancelar igual porque es necesario, por ej,
                # si no se va a entregar y ya está facturado y se quiere hacer
                # la nota de crédito. además se puede volver a subir la cantidad
                # si se requiere
                # if rec.qty_invoiced > rec.qty_delivered:
                #     raise ValidationError(_(
                #         'You can not cancel remianing qty to deliver because '
                #         'there are more product invoiced than the delivered. '
                #         'You should correct invoice or ask for a refund'))

                # Cancelamos el remanente SIN pasar por el procurement (skip_procurement).
                # Si redujéramos la cantidad dejando que se lance el stock rule, el core
                # genera un move NEGATIVO de compensación por cada tramo de la ruta
                # (ej. PICK y OUT en entregas de 2 pasos). Ese negativo solo se absorbe
                # si encuentra un move positivo NO 'done' en el mismo tramo; cuando la
                # contraparte ya está 'done' (stock pickeado a Salida) o todavía no
                # existe, el sobrante no puede mergearse y Odoo lo materializa como
                # contra-entrega (traslado reverso to_refund). En su lugar bajamos la
                # demanda y cancelamos directamente los moves pendientes de la línea
                # (= el remanente). Lo ya entregado/'done' no se toca. Ver ticket 118147.
                rec.with_context(skip_locked_order_line_check=True, skip_procurement=True).product_uom_qty = (
                    rec.qty_delivered + rec.quantity_returned
                )

                pending_moves = rec.move_ids.filtered(lambda m: m.state not in ("done", "cancel"))
                if pending_moves:
                    pending_moves.with_context(cancel_from_order=True, can_delete=True)._action_cancel()

                rec.order_id.message_post(
                    body=_('Cancel remaining call for line "%s" (id %s), line qty updated from %s to %s')
                    % (rec.name, rec.id, old_product_uom_qty, rec.product_uom_qty)
                )
        finally:
            # Volver a bloquear las órdenes que estaban bloqueadas sin generar mensaje.
            if orders_to_relock:
                orders_to_relock.with_context(tracking_disable=True).write({"locked": True})

    @api.onchange("product_uom_qty")
    def _onchange_product_uom_qty(self):
        """
        Sobre escribimos este método para no permitir reducir cantidad
        we do it this way for this reason:
        https://github.com/odoo/odoo/commit/
        8fe7229e1984811f3456dbf502cb03fba879e180
        """
        if self._origin:
            product_uom_qty_origin = self._origin.read(["product_uom_qty"])[0]["product_uom_qty"]
        else:
            product_uom_qty_origin = 0
        if (
            self.state == "sale"
            and self.product_id.type in ["product", "consu"]
            and self.product_uom_qty < product_uom_qty_origin
        ):
            warning_mess = {
                "title": _("Ordered quantity decreased!"),
                "message": (
                    "¡Está reduciendo la cantidad pedida! Recomendamos usar"
                    " el botón para cancelar remanente y"
                    " luego setear la cantidad deseada."
                ),
            }
            self.product_uom_qty = self._origin.product_uom_qty
            return {"warning": warning_mess}
        return {}

    @api.depends(
        "qty_delivered_method",
        "move_ids.state",
        "move_ids.scrapped",
        "move_ids.product_uom_qty",
        "move_ids.product_uom",
    )
    def _compute_quantity_returned(self):
        bom_enable = "bom_ids" in self.env["product.template"]._fields
        for order_line in self:
            quantity_returned = 0.0
            # we use same method as in odoo use to delivery's
            if order_line.qty_delivered_method == "stock_move":
                # Solo considerar devoluciones REALES del cliente, no contraentregas internas
                # Las devoluciones reales deben venir de ubicación 'customer' hacia ubicación no-customer
                return_moves = order_line.mapped("move_ids").filtered(
                    lambda r: (
                        r.state == "done"
                        and not r.scrapped
                        and r.location_dest_id.usage != "customer"
                        and r.location_id.usage == "customer"
                        and r.to_refund
                    )
                )
                # Kit component moves are skipped here: their returned quantity is computed
                # below by _compute_kit_quantities, and their UoM may belong to a different
                # category than the order line's.
                non_kit_moves = return_moves
                if bom_enable:
                    non_kit_moves = return_moves.filtered(lambda m: m.bom_line_id.bom_id.type != "phantom")
                for move in non_kit_moves:
                    quantity_returned += move.product_uom._compute_quantity(
                        move.product_uom_qty, order_line.product_uom
                    )
                if bom_enable:
                    boms = return_moves.mapped("bom_line_id.bom_id")
                    dropship = False
                    if not boms and any([m._is_dropshipped() for m in return_moves]):
                        boms = boms._bom_find(
                            products=order_line.product_id, company_id=order_line.company_id.id, bom_type="phantom"
                        )[order_line.product_id]
                        dropship = True
                    # We fetch the BoMs of type kits linked to the order_line,
                    # the we keep only the one related to the finished produst.
                    # This bom shoud be the only one since bom_line_id was written on the moves
                    relevant_bom = boms.filtered(
                        lambda b: (
                            b.type == "phantom"
                            and (
                                b.product_id == order_line.product_id
                                or (b.product_tmpl_id == order_line.product_id.product_tmpl_id and not b.product_id)
                            )
                        )
                    )
                    if relevant_bom:
                        # In case of dropship, we use a 'all or nothing' policy since 'bom_line_id' was
                        # not written on a move coming from a PO.
                        # FIXME: if the components of a kit have different suppliers, multiple PO
                        # are generated. If one PO is confirmed and all the others are in draft, receiving
                        # the products for this PO will set the qty_delivered. We might need to check the
                        # state of all PO as well... but sale_mrp doesn't depend on purchase.
                        if dropship:
                            if order_line.move_ids and all([m.state == "done" for m in return_moves]):
                                quantity_returned = order_line.product_uom_qty
                            else:
                                quantity_returned = 0.0
                            continue
                        filters = {
                            "outgoing_moves": lambda m: (
                                m.location_dest_id.usage == "customer"
                                and (not m.origin_returned_move_id or (m.origin_returned_move_id and m.to_refund))
                            ),
                            "incoming_moves": lambda m: (
                                m.location_dest_id.usage != "customer"
                                and m.location_id.usage == "customer"
                                and m.to_refund
                            ),
                        }
                        order_qty = order_line.product_uom._compute_quantity(
                            order_line.product_uom_qty, relevant_bom.product_uom_id
                        )
                        quantity_returned = return_moves._compute_kit_quantities(
                            order_line.product_id, order_qty, relevant_bom, filters
                        )

                    # If no relevant BOM is found, fall back on the all-or-nothing policy. This happens
                    # when the product sold is made only of kits. In this case, the BOM of the stock moves
                    # do not correspond to the product sold => no relevant BOM.
                    elif boms:
                        if all([m.state == "done" for m in return_moves]):
                            quantity_returned = order_line.product_uom_qty
                        else:
                            quantity_returned = 0.0
            order_line.quantity_returned = quantity_returned

    @api.depends("quantity_returned", "move_ids.state", "move_ids.product_uom_qty")
    def _compute_qty_to_invoice(self):
        """
        Modificamos la funcion original para que si el producto es segun lo
        pedido, para que funcione el reembolso hacemos que la cantidad a
        facturar reste la cantidad devuelta.
        """
        super()._compute_qty_to_invoice()
        for line in self:
            # igual que por defecto, si no en estos estados, no hay a facturar
            if line.order_id.state not in ["sale", "done"]:
                continue
            if line.product_id.invoice_policy == "order":
                # Simplemente usar quantity_returned que ya considera todas las devoluciones
                # incluyendo kits, dropship, etc. y excluye cancelaciones de remanente
                qty_to_invoice_corrected = line.product_uom_qty - line.quantity_returned - line.qty_invoiced
                line.qty_to_invoice = qty_to_invoice_corrected

    @api.depends(
        "order_id.force_invoiced_status",
        "state",
        "product_uom_qty",
        "qty_delivered",
        "qty_to_invoice",
        "qty_invoiced",
        "quantity_returned",
    )
    def _compute_invoice_status(self):
        super()._compute_invoice_status()
        precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        for line in self:
            if not line.order_id.force_invoiced_status:
                net_qty = line.product_uom_qty - line.quantity_returned
                if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    line.invoice_status = "to invoice"
                elif (
                    line.state == "sale"
                    and line.product_id.invoice_policy == "order"
                    and line.product_uom_qty >= 0.0
                    and float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) == 1
                ):
                    line.invoice_status = "upselling"
                elif float_compare(line.qty_invoiced, net_qty, precision_digits=precision) >= 0 and (
                    # Sin devolución mantenemos la semántica nativa (una línea de
                    # cantidad 0 queda "invoiced"). Con devolución solo es "invoiced"
                    # si quedó una cantidad neta positiva a facturar; si se devolvió
                    # todo (neto 0), no hay nada que facturar y cae a "no", igual que
                    # el core de Odoo. Ver ticket 123997.
                    float_is_zero(line.quantity_returned, precision_digits=precision)
                    or float_compare(net_qty, 0.0, precision_digits=precision) > 0
                ):
                    line.invoice_status = "invoiced"
                else:
                    line.invoice_status = "no"

    @api.depends("product_template_id")
    def _compute_stock_by_location(self):
        # Batched: a single grouped query for every product in the recordset instead
        # of a stock.quant read_group per line (avoids an N+1 on the order form load).
        self.stock_by_location = ""
        lines = self.filtered("product_id")
        if not lines:
            return

        available_by_product = defaultdict(list)
        for product, location, available_quantity in self.env["stock.quant"]._read_group(
            domain=[
                ("location_id.usage", "=", "internal"),
                ("product_id", "in", lines.product_id.ids),
                ("quantity", ">", 0),
            ],
            groupby=["product_id", "location_id"],
            aggregates=["available_quantity:sum"],
        ):
            if available_quantity > 0:
                available_by_product[product.id].append((location.display_name, available_quantity))

        for line in lines:
            stock_lines = []
            for location_name, free_qty in available_by_product.get(line.product_id.id, []):
                if line.product_uom and line.product_uom != line.product_id.uom_id:
                    free_qty = line.product_id.uom_id._compute_quantity(free_qty, line.product_uom)
                stock_lines.append(f"{location_name}: {free_qty:.2f} {line.product_uom.name}")
            line.stock_by_location = "\n".join(stock_lines)

    def _get_protected_fields(self):
        """Override to allow modifications when skip_locked_order_line_check context is set."""
        if self._context.get("skip_locked_order_line_check"):
            return []
        return super()._get_protected_fields()
