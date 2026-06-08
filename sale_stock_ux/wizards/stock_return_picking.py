##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    @api.model
    def default_get(self, fields):
        """Get sale order for lines."""
        result = super().default_get(fields)
        try:
            for line in result["product_return_moves"]:
                assert line[0] == 0
                # en realidad no nos importa si hay linea de venta o no ya que
                # también lo usamos en compras y queremos que en todo caso este
                line[2]["to_refund"] = True
        except KeyError:
            pass
        return result

    def action_create_exchanges(self):
        if any(self.product_return_moves.mapped("to_refund")):
            raise UserError(_("You cannot create exchanges for return lines marked to refund."))
        return super(StockReturnPicking, self.with_context(is_exchange_move=True)).action_create_exchanges()

    def action_create_returns(self):
        self.ensure_one()
        if self._is_return_of_sale_return() and not self.env.context.get("skip_return_of_sale_return_check"):
            return self._action_warn_return_of_sale_return()
        return super().action_create_returns()

    def _is_return_of_sale_return(self):
        """¿Esta devolución es, a su vez, una devolución ligada a una venta?

        Reenviar al cliente mercadería ya devuelta a través de una cadena de
        devoluciones puede dejar la orden de venta inconsistente en cantidades
        entregadas y/o estado de facturación (tickets 119865 / 119975). No se
        bloquea: se advierte y se deja continuar. Se exceptúa el contexto
        ``is_exchange_move`` (``action_create_exchanges``), que crea su
        contra-entrega de forma controlada y no genera la inconsistencia.
        """
        if self.env.context.get("is_exchange_move"):
            return False
        picking = self.picking_id
        # ``return_id`` solo está poblado cuando el picking ES, a su vez, una
        # devolución. ``sale_id`` acota la advertencia a pickings ligados a una
        # OV (en compras / movimientos sueltos "Para abonar" no repercute).
        return bool(picking.return_id and picking.sale_id)

    def _action_warn_return_of_sale_return(self):
        """Reabre el mismo wizard mostrando la advertencia no bloqueante."""
        self.ensure_one()
        _logger.info(
            "Devolución de una devolución ligada a la OV %s (picking %s): " "se solicita confirmación al usuario.",
            self.picking_id.sale_id.display_name,
            self.picking_id.name,
        )
        return {
            "name": _("Devolución de una devolución"),
            "type": "ir.actions.act_window",
            "res_model": "stock.return.picking",
            "res_id": self.id,
            "view_id": self.env.ref("stock.view_stock_return_picking_form").id,
            "view_mode": "form",
            "target": "new",
            "context": dict(self.env.context, show_return_of_return_warning=True),
        }


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    def _prepare_move_default_values(self, new_picking):
        vals = super()._prepare_move_default_values(new_picking)
        if self.env.context.get("is_exchange_move"):
            vals["is_exchange_move"] = True
        return vals

    def _prepare_picking_default_values_based_on(self, picking):
        vals = super()._prepare_picking_default_values_based_on(picking)
        if self.env.context.get("is_exchange_move"):
            vals["is_exchange_move"] = True
        return vals
