##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReturnExchangeDemand(TransactionCase):
    """Regresion ticket 120871.

    Sobre una OV entregada, una 1ra devolucion con reembolso deja
    ``quantity_returned > 0``. El HACK de ``stock.move.create`` restaba esa
    cantidad a TODO move nuevo con ``sale_line_id``, corrompiendo la demanda de
    la 2da operacion (otra devolucion o una devolucion para cambio):
    nacian con ``demanda = cantidad - quantity_returned`` en vez de la cantidad
    pedida. El fix acota el descuento a entregas genuinas.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "Test Return Product", "list_price": 100.0, "type": "consu", "is_storable": True}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test Return Partner", "customer_rank": 1})
        # evitar errores de reglas de excepcion en runbot
        if cls.env["sale.order"]._fields.get("ignore_exception"):
            cls.env["exception.rule"].search([("active", "=", True)]).write({"active": False})

    def _new_order(self, qty=10):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": qty, "price_unit": 100.0})],
            }
        )
        order.action_confirm()
        return order

    def _validate(self, picking):
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.move_ids.picked = True
        picking._action_done()

    def _return_wizard(self, picking, qty, to_refund):
        wizard = Form(
            self.env["stock.return.picking"].with_context(
                active_id=picking.id, active_ids=picking.ids, active_model="stock.picking"
            )
        ).save()
        wizard.product_return_moves.quantity = qty
        wizard.product_return_moves.to_refund = to_refund
        return wizard

    def test_second_return_demand(self):
        """1ra devolucion con reembolso (2u) + 2da devolucion (3u): la 2da debe
        nacer con demanda 3, no 3 - 2."""
        order = self._new_order(qty=10)
        delivery = order.picking_ids
        self._validate(delivery)

        # 1ra devolucion 2u con reembolso -> quantity_returned = 2
        first = self._return_wizard(delivery, qty=2, to_refund=True)
        first_pick = self.env["stock.picking"].browse(first.action_create_returns()["res_id"])
        self._validate(first_pick)
        self.assertEqual(order.order_line.quantity_returned, 2.0)

        # 2da devolucion 3u sobre la misma entrega
        second = self._return_wizard(delivery, qty=3, to_refund=True)
        second_pick = self.env["stock.picking"].browse(second.action_create_returns()["res_id"])

        self.assertEqual(
            second_pick.move_ids.product_uom_qty,
            3.0,
            "La 2da devolucion debe pedir 3u; el hack la dejaba en 3 - quantity_returned.",
        )

    def test_return_then_exchange_demand(self):
        """1ra devolucion con reembolso (2u) + devolucion para cambio (3u): los
        moves de cambio deben nacer con demanda 3, no 3 - 2."""
        order = self._new_order(qty=10)
        delivery = order.picking_ids
        self._validate(delivery)

        # 1ra devolucion 2u con reembolso -> quantity_returned = 2
        first = self._return_wizard(delivery, qty=2, to_refund=True)
        first_pick = self.env["stock.picking"].browse(first.action_create_returns()["res_id"])
        self._validate(first_pick)
        self.assertEqual(order.order_line.quantity_returned, 2.0)

        # devolucion para cambio 3u (to_refund debe quedar False para crear cambios)
        exchange = self._return_wizard(delivery, qty=3, to_refund=False)
        exchange.action_create_exchanges()

        exchange_moves = order.order_line.move_ids.filtered(lambda m: m.is_exchange_move)
        self.assertTrue(exchange_moves, "Deberian existir movimientos marcados como cambio.")
        for move in exchange_moves:
            self.assertEqual(
                move.product_uom_qty,
                3.0,
                "Los movimientos de cambio deben pedir 3u; el hack los dejaba en 3 - quantity_returned.",
            )
