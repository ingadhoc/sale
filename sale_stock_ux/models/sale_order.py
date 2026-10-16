##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.float_utils import float_compare


class SaleOrder(models.Model):
    _inherit = "sale.order"

    delivery_status = fields.Selection(
        selection_add=[
            ("no", "Nothing to Deliver"),
        ],
        readonly=True,
        default="no",
    )
    force_delivery_status = fields.Selection(
        [
            ("no", "Nothing to Deliver"),
            ("full", "Fully Delivered"),
        ],
        tracking=True,
        copy=False,
    )

    with_returns = fields.Boolean(
        compute="_compute_with_returns",
        store=True,
    )

    @api.depends("order_line.quantity_returned")
    def _compute_with_returns(self):
        for order in self:
            order.with_returns = any(line.quantity_returned for line in order.order_line)

    def _check_cancel_allowed(self):
        delivered = self.filtered(lambda order: order.picking_ids.filtered(lambda x: x.state == "done"))
        if delivered:
            raise UserError(
                _(
                    "Unable to cancel sale order %s as some deliveries have already been done.",
                    ", ".join(delivered.mapped("display_name")),
                )
            )
        return super()._check_cancel_allowed()

    def action_cancel(self):
        return super(SaleOrder, self.with_context(cancel_from_order=True)).action_cancel()

    @api.depends("picking_ids", "picking_ids.state", "force_delivery_status")
    def _compute_delivery_status(self):
        super()._compute_delivery_status()
        for order in self:
            if not order.picking_ids or all(p.state == "cancel" for p in order.picking_ids):
                order.delivery_status = "no"
                continue
            if order.force_delivery_status:
                order.delivery_status = order.force_delivery_status
                continue

    def write(self, vals):
        self.check_force_delivery_status(vals)
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.check_force_delivery_status(vals)
        return super().create(vals_list)

    @api.model
    def check_force_delivery_status(self, vals):
        if vals.get("force_delivery_status") and not self.env.user.has_group("base.group_system"):
            group = self.env.ref("base.group_system").sudo()
            raise UserError(
                _('Only users with "%s / %s" can Set Delivered manually') % (group.category_id.name, group.name)
            )

    def _get_protected_fields(self):
        return super()._get_protected_fields() + ["picking_policy", "warehouse_id"]

    # -- Contra-entregas fantasma al cancelar remanente (tarea 73048) --------
    # Al bajar la cantidad de una linea, el core lanza un procurement negativo
    # (el "espejo"). Si ese espejo no llega a fusionarse con el movimiento de
    # salida original (la llave del merge difiere por location_id, date_deadline,
    # etc.), no se netea, se invierte y sobrevive como una contra-entrega
    # fantasma (Cliente -> interno) que deja el original huerfano. La v1 NO
    # corrige: detecta, avisa, y ofrece al usuario un boton para sanear cuando
    # el mismo decida.

    _PHANTOM_ALIVE_STATES = ("draft", "confirmed", "waiting", "assigned", "partially_available")

    # Beta opt-in: el aviso y el boton de saneo solo operan si el parametro de
    # sistema `sale_stock_ux.sanity_pickings` esta activo. Apagado por default;
    # se prende por base a medida que se valida el comportamiento.
    _PHANTOM_BETA_PARAM = "sale_stock_ux.sanity_pickings"

    has_phantom_counterdelivery = fields.Boolean(
        compute="_compute_has_phantom_counterdelivery",
        search="_search_has_phantom_counterdelivery",
        help="Hay al menos una contra-entrega fantasma (movimiento invertido "
        "Cliente -> interno, vivo, nacido de un cancel de remanente que no neteo).",
    )

    def _phantom_beta_enabled(self):
        param = self.env["ir.config_parameter"].sudo().get_param(self._PHANTOM_BETA_PARAM)
        return str(param).strip().lower() in ("1", "true", "t", "yes")

    @api.model
    def _phantom_move_domain(self):
        """Patron de la contra-entrega fantasma, en una sola definicion reusada
        por la deteccion (in-memory) y por el filtro (search): movimiento
        invertido Cliente -> interno, vivo, `to_refund`, sin `origin_returned`."""
        return [
            ("state", "in", list(self._PHANTOM_ALIVE_STATES)),
            ("to_refund", "=", True),
            ("origin_returned_move_id", "=", False),
            ("location_id.usage", "=", "customer"),
            ("location_dest_id.usage", "=", "internal"),
        ]

    @api.depends(
        "picking_ids.move_ids.state",
        "picking_ids.move_ids.to_refund",
        "picking_ids.move_ids.origin_returned_move_id",
    )
    def _compute_has_phantom_counterdelivery(self):
        enabled = self._phantom_beta_enabled()
        for order in self:
            order.has_phantom_counterdelivery = enabled and bool(order._detect_phantom_counterdeliveries())

    def _detect_phantom_counterdeliveries(self):
        """Movimientos fantasma de este pedido: filtro in-memory sobre sus
        propios moves usando `_phantom_move_domain` (misma regla que el search)."""
        self.ensure_one()
        return self.picking_ids.move_ids.filtered_domain(self._phantom_move_domain())

    def _search_has_phantom_counterdelivery(self, operator, value):
        """Filtro performante: una sola query indexada sobre stock.move con el
        patron fantasma; devuelve los pedidos alcanzados. No usa campo stored."""
        if operator not in ("=", "!="):
            raise UserError(_("Operador no soportado para el filtro de contra-entregas fantasma."))
        positive = (operator == "=") == bool(value)
        if not self._phantom_beta_enabled():
            # Beta apagado: el filtro no matchea nada (evita confundir).
            return [("id", "=", False)] if positive else []
        domain = self._phantom_move_domain() + [("sale_line_id", "!=", False)]
        order_ids = self.env["stock.move"].search(domain).sale_line_id.order_id.ids
        return [("id", "in" if positive else "not in", order_ids)]

    def _phantom_activity_summary(self):
        return _("Posible(s) contra-entrega(s) fantasma")

    def _notify_phantom_counterdeliveries(self):
        """Levanta una actividad de aviso si se detecta el patron. No modifica
        stock. Evita duplicar una actividad abierta del mismo tipo. Beta: solo
        opera si `sale_stock_ux.sanity_pickings` esta activo."""
        if not self._phantom_beta_enabled():
            return
        summary = self._phantom_activity_summary()
        for order in self:
            moves = order._detect_phantom_counterdeliveries()
            if not moves or order.activity_ids.filtered(lambda a: a.summary == summary):
                continue
            note = _(
                "Se detectaron %(count)s movimiento(s) invertido(s) (Cliente -> interno) que parecen "
                "contra-entregas fantasma generadas al cancelar remanente: %(pickings)s.\n"
                "Revisar antes de validarlos. Si corresponde, usar el boton "
                '"Sanear contra-entregas fantasma" en el pedido.'
            ) % {"count": len(moves), "pickings": ", ".join(moves.picking_id.mapped("name"))}
            order.activity_schedule(
                "mail.mail_activity_data_warning",
                summary=summary,
                note=note,
                user_id=order.user_id.id or self.env.uid,
            )

    def _phantom_reverse_chain(self, entry):
        """Cadena inversa del fantasma, recorrida desde la entrada Cliente->interno
        por `move_orig_ids`/`move_dest_ids` y juntando solo patas de put-back vivas
        (`to_refund`, no genuinas).

        Discrimina por CONECTIVIDAD, no por `to_refund` suelto: un put-back interno
        legitimo de otra linea (devolver a Stock lo ya movido) tambien es `to_refund`,
        pero vive en un componente separado del grafo, sin entrada Cliente->interno,
        asi que no se alcanza desde `entry` y no se toca. Es el caso que un barrido
        plano por `to_refund` cancelaba por error, varando stock."""
        chain = entry
        frontier = entry
        while frontier:
            neigh = (frontier.move_orig_ids | frontier.move_dest_ids).filtered(
                lambda m: m.state in self._PHANTOM_ALIVE_STATES
                and not m.origin_returned_move_id
                and m.to_refund
                and m not in chain
            )
            if not neigh:
                break
            chain |= neigh
            frontier = neigh
        return chain

    def _phantom_footprint_moves(self):
        """Footprint completo del fantasma en el grupo de aprovisionamiento.

        La contra-entrega real en multi-paso no es un solo move: es una cadena
        inversa encadenada (Cliente->Despacho + patas internas de put-back
        Despacho->Zona->Stock), toda `to_refund`, y puede dejar ademas una cadena
        forward espuria para un producto que ya no tiene demanda. Este metodo junta
        todo eso, excluyendo SIEMPRE las devoluciones genuinas
        (`origin_returned_move_id`) y los put-backs legitimos de otras lineas (que
        no cuelgan de la entrada fantasma).

        Se dispara solo si hay una contra-entrega Cliente->interno detectada.
        """
        self.ensure_one()
        entry = self._detect_phantom_counterdeliveries()
        if not entry:
            return entry
        precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        # Candidatos para la cadena forward espuria: moves vivos del grupo Y de los
        # pickings del pedido (por si alguna pata quedó sin group_id), excluyendo
        # devoluciones genuinas.
        candidates = self.picking_ids.move_ids
        if self.procurement_group_id:
            candidates |= self.env["stock.move"].search([("group_id", "=", self.procurement_group_id.id)])
        candidates = candidates.filtered(
            lambda m: m.state in self._PHANTOM_ALIVE_STATES and not m.origin_returned_move_id
        )
        # 1) cadena inversa del fantasma, siguiendo el encadenamiento desde la entrada
        footprint = self._phantom_reverse_chain(entry)
        # 2) para cada producto con fantasma, si el pedido ya no tiene demanda
        #    restante de ese producto, la entrega forward tambien es espuria. Solo
        #    barremos moves FORWARD (destino cliente): un put-back interno legitimo
        #    del mismo producto (interno->interno/Stock) devuelve al deposito lo ya
        #    movido y no debe cancelarse aunque la demanda quede en cero.
        for product in entry.product_id:
            lines = self.order_line.filtered(lambda line: line.product_id == product)
            remaining = sum(line.product_uom_qty - line.qty_delivered - line.quantity_returned for line in lines)
            if float_compare(remaining, 0, precision_digits=precision) <= 0:
                footprint |= candidates.filtered(
                    lambda m: m.product_id == product and m.location_dest_id.usage == "customer"
                )
        return footprint

    def _phantom_forward_orphan_moves(self):
        """Legs FORWARD vivos que el cancel de remanente dejo "en espera".

        Cuando el core arma la contra-entrega en vez de cancelar los pendientes,
        no solo nace la cadena inversa (Cliente->interno) sino que los tramos
        forward de la entrega (PICK/PACK/OUT) quedan vivos demandando una cantidad
        que la orden ya no necesita. El deposito los cancela a mano: justo lo que
        el ticket pide evitar. Los sumamos al saneo cuando la linea del producto
        con fantasma ya no tiene demanda restante.

        Discrimina por `to_refund=False` (forward, no put-back) y excluye
        devoluciones genuinas; solo barre productos que TIENEN una entrada fantasma
        detectada, asi el saneo sigue acotado al pedido roto.
        """
        self.ensure_one()
        entry = self._detect_phantom_counterdeliveries()
        if not entry:
            return self.env["stock.move"]
        precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        candidates = self.picking_ids.move_ids
        if self.procurement_group_id:
            candidates |= self.env["stock.move"].search([("group_id", "=", self.procurement_group_id.id)])
        stock_loc = self.warehouse_id.lot_stock_id

        def _to_stock(move):
            dest = move.location_dest_id
            return bool(dest.parent_path) and dest.parent_path.startswith(stock_loc.parent_path)

        candidates = candidates.filtered(
            lambda m: m.state in self._PHANTOM_ALIVE_STATES
            and not m.to_refund
            and not m.origin_returned_move_id
            and m.location_id.usage == "internal"
            and m.location_dest_id.usage in ("internal", "customer")
            # solo tramos FORWARD (hacia el cliente); nunca un retorno a Stock
            and not _to_stock(m)
        )
        orphans = self.env["stock.move"]
        for product in entry.product_id:
            lines = self.order_line.filtered(lambda line: line.product_id == product)
            remaining = sum(line.product_uom_qty - line.qty_delivered - line.quantity_returned for line in lines)
            if float_compare(remaining, 0, precision_digits=precision) <= 0:
                orphans |= candidates.filtered(lambda m: m.product_id == product)
        return orphans

    def _phantom_return_stranded_transit(self):
        """Devuelve a Stock lo que quede FISICAMENTE varado en una ubicacion
        intermedia tras cancelar la cadena.

        Al cancelar un leg forward cuyo tramo anterior ya estaba hecho, las
        unidades quedan en una zona intermedia (p.ej. Zona de picking / Salida)
        sin un movimiento que las saque. Calculamos el neto por (producto,
        ubicacion intermedia) de los movimientos DONE del grupo (entradas menos
        salidas, sin contar devoluciones genuinas) y, por cada neto positivo,
        creamos un movimiento interno de retorno a Stock. No se auto-valida: lo
        confirma el operario. Si no hay nada varado, no crea nada."""
        self.ensure_one()
        if not self.procurement_group_id:
            return self.env["stock.move"]
        precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        stock_loc = self.warehouse_id.lot_stock_id
        # Fuente: los moves del pedido Y los del grupo (consistente con los otros
        # metodos del fantasma). Juntar ambos cubre un move cuyo group_id quedo
        # desincronizado pero sigue colgando de un picking del pedido.
        group_moves = self.picking_ids.move_ids
        if self.procurement_group_id:
            group_moves |= self.env["stock.move"].search([("group_id", "=", self.procurement_group_id.id)])
        done = group_moves.filtered(lambda m: m.state == "done" and not m.origin_returned_move_id)

        def _is_stock(loc):
            return bool(loc.parent_path) and loc.parent_path.startswith(stock_loc.parent_path)

        net = {}  # (product, location) -> qty en uom del producto
        for m in done:
            qty = m.product_uom._compute_quantity(m.quantity, m.product_id.uom_id)
            if m.location_dest_id.usage == "internal" and not _is_stock(m.location_dest_id):
                net[(m.product_id, m.location_dest_id)] = net.get((m.product_id, m.location_dest_id), 0.0) + qty
            if m.location_id.usage == "internal" and not _is_stock(m.location_id):
                net[(m.product_id, m.location_id)] = net.get((m.product_id, m.location_id), 0.0) - qty
        # Restar lo que un movimiento VIVO sobreviviente ya saca de esa ubicacion:
        # si el core dejo un put-back legitimo, o un tramo forward con demanda sigue
        # vivo, esas unidades ya tienen salida y NO hay que volver a devolverlas.
        # Corre despues de cancelar, asi los legs ya cancelados no cuentan aca.
        alive = group_moves.filtered(lambda m: m.state in self._PHANTOM_ALIVE_STATES and not m.origin_returned_move_id)
        for m in alive:
            if m.location_id.usage == "internal" and not _is_stock(m.location_id):
                out_qty = m.product_uom._compute_quantity(m.product_uom_qty, m.product_id.uom_id)
                key = (m.product_id, m.location_id)
                if key in net:
                    net[key] -= out_qty
        returns = self.env["stock.move"]
        int_type = self.warehouse_id.int_type_id
        for (product, loc), qty in net.items():
            if float_compare(qty, 0, precision_digits=precision) <= 0:
                continue
            picking = self.env["stock.picking"].create(
                {
                    "picking_type_id": int_type.id,
                    "location_id": loc.id,
                    "location_dest_id": stock_loc.id,
                    "group_id": self.procurement_group_id.id,
                    "origin": _("Saneo contra-entrega %s") % self.name,
                }
            )
            mv = self.env["stock.move"].create(
                {
                    "name": product.display_name,
                    "product_id": product.id,
                    "product_uom": product.uom_id.id,
                    "product_uom_qty": qty,
                    "location_id": loc.id,
                    "location_dest_id": stock_loc.id,
                    "picking_id": picking.id,
                    "group_id": self.procurement_group_id.id,
                }
            )
            mv._action_confirm()
            mv._action_assign()
            returns |= mv
        return returns

    def action_sanitize_phantom_counterdeliveries(self):
        """Saneo MANUAL, disparado por el usuario: cancela el footprint completo
        del fantasma (cadena inversa + forward espuria del producto sin demanda)
        MAS los tramos forward que quedaron "en espera" por el mismo cancel, y
        devuelve a Stock lo que haya quedado fisicamente varado. No toca
        devoluciones genuinas. Requiere el beta activo y permiso maximo de
        inventario."""
        self.ensure_one()
        if not self._phantom_beta_enabled():
            raise UserError(_("El saneo de contra-entregas fantasma no esta habilitado en esta base."))
        if not self.env.user.has_group("stock.group_stock_manager"):
            raise AccessError(_("Solo un administrador de Inventario puede sanear contra-entregas fantasma."))
        moves = self._phantom_footprint_moves() | self._phantom_forward_orphan_moves()
        if not moves:
            raise UserError(_("No hay contra-entregas fantasma para sanear en este pedido."))
        moves.with_context(cancel_from_order=True)._action_cancel()
        self._phantom_return_stranded_transit()
        self.message_post(
            body=_("Se sanearon %(count)s movimiento(s) de contra-entrega fantasma: %(pickings)s.")
            % {"count": len(moves), "pickings": ", ".join(moves.picking_id.mapped("name"))}
        )
        # cerrar la actividad de aviso, si quedo abierta
        summary = self._phantom_activity_summary()
        self.activity_ids.filtered(lambda a: a.summary == summary).action_done()
        return True
