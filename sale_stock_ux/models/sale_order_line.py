##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
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
        for line in self:
            loc_id = line.order_id.warehouse_id.lot_stock_id.id
            stock_quants = self.env["stock.quant"].search(
                [("product_id", "=", line.product_id.id), ("location_id", "child_of", loc_id)]
            )
            line.total_reserved_quantity = sum(stock_quants.mapped("reserved_quantity"))

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

    def _get_delivery_moves_chain(self):
        """Cadena completa de entrega (OUT + PACK + PICK). En multi-paso MTO/pull
        ``move_ids`` solo trae los OUT (los pasos internos no llevan ``sale_line_id``),
        así que subimos por ``move_orig_ids`` con el helper nativo de core. Ver ticket
        122299."""
        self.ensure_one()
        return self.env["stock.move"].browse(self.move_ids._rollup_move_origs())

    def _cancel_or_reduce_chain(self, chain, reduce_qty):
        """Saca ``reduce_qty`` de demanda pendiente de la cadena de entrega.

        En MTO/pull los pasos internos (PICK/PACK) no llevan ``sale_line_id`` y el core
        los FUSIONA entre líneas del mismo producto. Por eso, en cada tramo pendiente,
        si su cantidad es <= al remanente lo cancelamos (es exclusivo de esta línea) y
        si es mayor lo reducimos (move fusionado: conservamos la parte de las otras
        líneas). ``reduce_qty`` viene en la UoM de la línea; convertimos por move.
        Ver ticket 122299."""
        self.ensure_one()
        pending = chain.filtered(lambda m: m.state not in ("done", "cancel") and m.location_id.usage != "customer")
        for move in pending:
            reduce_in_move = self.product_uom._compute_quantity(reduce_qty, move.product_uom, rounding_method="HALF-UP")
            if float_compare(move.product_uom_qty, reduce_in_move, precision_rounding=move.product_uom.rounding) <= 0:
                # cancel_from_order evita el constraint check_cancel de stock_ux, que bloquea
                # a usuarios sin el permiso 'Picking cancelation allow' (ticket 122867).
                move.with_context(cancel_from_order=True)._action_cancel()
            else:
                move.product_uom_qty -= reduce_in_move
                move._action_assign()

    def _return_remaining_transit(self, chain, remnant):
        """Devuelve a Stock lo que quedó en tránsito en ubicaciones intermedias.

        Lo ya movido a un paso intermedio (ej. PICK/PACK validados) que ya no va a
        salir queda parado ahí, y un move ``done`` no se puede cancelar. Calculamos la
        posición NETA de la cadena por ubicación (entra +, sale -) y, por cada interna
        ≠ Stock con neto > 0, generamos un retorno directo a Stock. Trabajar por neto
        (en vez de tramo a tramo) resuelve también el multi-nivel PICK+PACK ambos done.
        El total devuelto se topea en ``remnant`` (lo cancelado por ESTA línea): si los
        moves están fusionados con otras líneas, el neto incluye cantidad ajena que no
        hay que devolver. Queda pendiente de validar, como cualquier contraentrega.
        Ver ticket 122299."""
        self.ensure_one()
        product_uom = self.product_uom
        rounding = product_uom.rounding
        warehouse = self.order_id.warehouse_id
        stock_location = warehouse.lot_stock_id
        net = {}
        for move in chain.filtered(lambda m: m.state == "done"):
            qty = move.product_uom._compute_quantity(move.quantity, product_uom, rounding_method="HALF-UP")
            net[move.location_dest_id] = net.get(move.location_dest_id, 0.0) + qty
            net[move.location_id] = net.get(move.location_id, 0.0) - qty

        group = self.move_ids[:1].group_id
        budget = remnant
        vals = []
        for location, qty in net.items():
            if location == stock_location or location.usage != "internal":
                continue
            qty = min(qty, budget)
            if float_compare(qty, 0.0, precision_rounding=rounding) <= 0:
                continue
            budget -= qty
            vals.append(
                {
                    "name": _("Cancel remaining return: %s") % (self.name or self.product_id.display_name),
                    "product_id": self.product_id.id,
                    "product_uom": product_uom.id,
                    "product_uom_qty": qty,
                    "location_id": location.id,
                    "location_dest_id": stock_location.id,
                    "picking_type_id": warehouse.int_type_id.id,
                    "warehouse_id": warehouse.id,
                    "company_id": self.order_id.company_id.id,
                    "group_id": group.id if group else False,
                    "origin": self.order_id.name,
                    "procure_method": "make_to_stock",
                }
            )
        return_moves = self.env["stock.move"].create(vals)
        if return_moves:
            return_moves._action_confirm()
            return_moves._action_assign()
        return return_moves

    def button_cancel_remaining(self):
        # la cancelación de kits no está bien resuelta ya que odoo solo computa
        # la cantidad entregada cuando todo el kit se entregó. Cuestión que,
        # por ahora, desactivamos la cancelación de kits

        # Manejar órdenes bloqueadas: desbloquear temporalmente sin tracking
        orders_to_relock = self.mapped("order_id").filtered(lambda o: o.locked)
        if orders_to_relock:
            orders_to_relock.with_context(tracking_disable=True).write({"locked": False})

        pack_enable = "pack_ok" in self.env["product.template"]._fields
        for rec in self.filtered("product_id"):
            # For product pack compatibility to cancel all of componept in case the product parent is cancel
            if pack_enable and rec.product_id.pack_ok and rec.pack_type == "detailed" and rec.pack_child_line_ids:
                rec.pack_child_line_ids.with_context(cancel_from_order=True).button_cancel_remaining()

            old_product_uom_qty = rec.product_uom_qty
            target_qty = rec.qty_delivered + rec.quantity_returned
            remnant = old_product_uom_qty - target_qty
            if float_compare(remnant, 0.0, precision_rounding=rec.product_uom.rounding) <= 0:
                continue  # nada para cancelar (línea ya entregada o sobre-entregada)

            # Elegimos entre tres estrategias según el estado de la cadena de entrega
            # (OUT + PACK + PICK; ``move_ids`` solo trae los OUT en MTO, por eso subimos
            # por ``move_orig_ids``). La idea es respetar el flujo NATIVO de Odoo siempre
            # que produzca un resultado consistente, y solo tomar el control manual en
            # las topologías donde el recálculo nativo deja demanda huérfana o stock
            # varado (ver tickets 121400 / 122299 / 122867 y el banco de pruebas).
            chain = rec._get_delivery_moves_chain()
            in_transit = chain.filtered(
                lambda m: m.state == "done"
                and m.location_id.usage != "customer"
                and m.location_dest_id.usage != "customer"
            )
            internal_moves = chain.filtered(
                lambda m: m.state != "cancel"
                and m.location_id.usage != "customer"
                and m.location_dest_id.usage != "customer"
            )
            # En entregas MTO/pull los pasos internos no llevan ``sale_line_id``: el
            # recálculo nativo no puede reducirlos ni encadenar bien el retorno
            # multinivel, así que necesitamos manejo explícito. En cambio, en el esquema
            # progresivo (push, cada move con ``sale_line_id``) el nativo hace lo correcto.
            is_mto_chain = any(not m.sale_line_id for m in internal_moves)

            if not in_transit:
                # (1) Sin stock en tránsito: el remanente nunca se movió. Delegar generaría
                # la contraentrega fantasma del 121400 (sub-ubicación) o dejaría PICK/PACK
                # vivos en MTO (122299). Cancelamos/reducimos la cadena pendiente y bajamos
                # con ``skip_procurement`` para no relanzar la regla.
                rec._cancel_or_reduce_chain(chain, remnant)
                rec.with_context(skip_locked_order_line_check=True, skip_procurement=True).product_uom_qty = target_qty
            elif not is_mto_chain:
                # (2) Con tránsito, esquema PROGRESIVO: delegamos al recálculo nativo, que
                # reduce los pendientes y genera el retorno leg-by-leg (contraentrega
                # legítima) registrando la actividad de aviso estándar de Odoo.
                rec.with_context(skip_locked_order_line_check=True).product_uom_qty = target_qty
            else:
                # (3) Con tránsito, esquema MTO: el nativo deja demanda forward huérfana
                # (entrega parcial) o el retorno multinivel a medias (caso PICK+PACK done).
                # Cancelamos la cadena pendiente, devolvemos a Stock lo que quedó en
                # tránsito, y bajamos con ``skip_procurement``.
                rec._cancel_or_reduce_chain(chain, remnant)
                rec._return_remaining_transit(chain, remnant)
                rec.with_context(skip_locked_order_line_check=True, skip_procurement=True).product_uom_qty = target_qty
            rec.order_id.message_post(
                body=_('Cancel remaining call for line "%s" (id %s), line qty updated from %s to %s')
                % (rec.name, rec.id, old_product_uom_qty, rec.product_uom_qty)
            )

        # Volver a bloquear las órdenes que estaban bloqueadas sin generar mensaje
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
                # In multi-step deliveries, we need to avoid counting the same return multiple times
                for move in return_moves.filtered(lambda m: m.location_id.usage == "customer"):
                    quantity_returned += move.product_uom._compute_quantity(
                        move.product_uom_qty, order_line.product_uom
                    )
                bom_enable = "bom_ids" in self.env["product.template"]._fields
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
        "order_id.force_invoiced_status", "state", "product_uom_qty", "qty_delivered", "qty_to_invoice", "qty_invoiced"
    )
    def _compute_invoice_status(self):
        super()._compute_invoice_status()
        precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        for line in self:
            if not line.order_id.force_invoiced_status:
                if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    line.invoice_status = "to invoice"
                elif (
                    line.state == "sale"
                    and line.product_id.invoice_policy == "order"
                    and line.product_uom_qty >= 0.0
                    and float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) == 1
                ):
                    line.invoice_status = "upselling"
                elif (
                    float_compare(
                        line.qty_invoiced, (line.product_uom_qty - line.quantity_returned), precision_digits=precision
                    )
                    >= 0
                ):
                    line.invoice_status = "invoiced"
                else:
                    line.invoice_status = "no"

    @api.depends("product_template_id")
    def _compute_stock_by_location(self):
        for line in self:
            if not line.product_id:
                line.stock_by_location = ""
                continue

            stock_quants = self.env["stock.quant"].read_group(
                domain=[
                    ("location_id.usage", "=", "internal"),
                    ("product_id", "=", line.product_id.id),
                    ("quantity", ">", 0),
                ],
                fields=["location_id", "available_quantity:sum"],
                groupby=["location_id"],
                lazy=False,
            )

            stock_lines = []

            for stock in stock_quants:
                location_name = stock["location_id"][1]
                free_qty = stock["available_quantity"]

                if free_qty > 0:
                    if line.product_uom and line.product_uom != line.product_id.uom_id:
                        free_qty = line.product_id.uom_id._compute_quantity(free_qty, line.product_uom)

                    stock_lines.append(f"{location_name}: {free_qty:.2f} {line.product_uom.name}")

            line.stock_by_location = "\n".join(stock_lines) if stock_lines else ""

        (self - self).stock_by_location = ""

    def _get_protected_fields(self):
        """Override to allow modifications when skip_locked_order_line_check context is set."""
        if self._context.get("skip_locked_order_line_check"):
            return []
        return super()._get_protected_fields()
