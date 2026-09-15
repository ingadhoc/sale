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

    def action_cancel(self):
        self = self.with_context(cancel_from_order=True)
        for order in self.filtered(lambda order: order.picking_ids.filtered(lambda x: x.state == "done")):
            raise UserError(
                _("Unable to cancel sale order %s as some deliveries" " have already been done.") % (order.name)
            )
        return super().action_cancel()

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

    def _phantom_footprint_moves(self):
        """Footprint completo del fantasma en el grupo de aprovisionamiento.

        La contra-entrega real en multi-paso no es un solo move: es una cadena
        inversa (Cliente->Despacho + patas internas de put-back Despacho->Zona->
        Stock), toda `to_refund`, y puede dejar ademas una cadena forward espuria
        para un producto que ya no tiene demanda. Este metodo junta todo eso,
        excluyendo SIEMPRE las devoluciones genuinas (`origin_returned_move_id`).

        Se dispara solo si hay una contra-entrega Cliente->interno detectada.
        """
        self.ensure_one()
        entry = self._detect_phantom_counterdeliveries()
        if not entry:
            return entry
        precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        # Candidatos: moves vivos del grupo Y de los pickings del pedido (por si
        # alguna pata quedó sin group_id), excluyendo devoluciones genuinas.
        candidates = self.picking_ids.move_ids
        if self.procurement_group_id:
            candidates |= self.env["stock.move"].search(
                [("group_id", "=", self.procurement_group_id.id)]
            )
        candidates = candidates.filtered(
            lambda m: m.state in self._PHANTOM_ALIVE_STATES and not m.origin_returned_move_id
        )
        # 1) toda la cadena inversa to_refund (entry + patas internas de put-back)
        footprint = entry | candidates.filtered(lambda m: m.to_refund)
        # 2) para cada producto con fantasma, si el pedido ya no tiene demanda
        #    restante de ese producto, la cadena forward tambien es espuria
        for product in entry.product_id:
            lines = self.order_line.filtered(lambda line: line.product_id == product)
            remaining = sum(
                line.product_uom_qty - line.qty_delivered - line.quantity_returned for line in lines
            )
            if float_compare(remaining, 0, precision_digits=precision) <= 0:
                footprint |= candidates.filtered(lambda m: m.product_id == product)
        return footprint

    def action_sanitize_phantom_counterdeliveries(self):
        """Saneo MANUAL, disparado por el usuario: cancela el footprint completo
        del fantasma (cadena inversa + forward espuria del producto sin demanda),
        sin tocar devoluciones genuinas. Requiere permiso maximo de inventario."""
        self.ensure_one()
        if not self.env.user.has_group("stock.group_stock_manager"):
            raise AccessError(_("Solo un administrador de Inventario puede sanear contra-entregas fantasma."))
        moves = self._phantom_footprint_moves()
        if not moves:
            raise UserError(_("No hay contra-entregas fantasma para sanear en este pedido."))
        moves.with_context(cancel_from_order=True)._action_cancel()
        self.message_post(
            body=_("Se sanearon %(count)s movimiento(s) de contra-entrega fantasma: %(pickings)s.")
            % {"count": len(moves), "pickings": ", ".join(moves.picking_id.mapped("name"))}
        )
        # cerrar la actividad de aviso, si quedo abierta
        summary = self._phantom_activity_summary()
        self.activity_ids.filtered(lambda a: a.summary == summary).action_done()
        return True
