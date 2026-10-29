##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReturnExchangeDemand(TransactionCase):
    """Devoluciones y cambios con el flujo de Odoo 20 (albarán de devolución y botón Exchange).

    Regresión ticket 120871: una 2da devolución no debe nacer con su demanda
    descontada por lo ya devuelto. Y un cambio (Exchange) vuelve a entregar lo
    devuelto, así que lo entregado vuelve a subir.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Return Product",
                "list_price": 100.0,
                "type": "consu",
                "is_storable": True,
                "invoice_policy": "order",
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test Return Partner", "customer_rank": 1})
        warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.env["stock.quant"]._update_available_quantity(cls.product, warehouse.lot_stock_id, 100.0)
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
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.move_ids.picked = True
        picking._action_done()

    def _return(self, picking, qty):
        returned = self.env["stock.picking"].browse(picking.action_return()["res_id"])
        returned.move_ids.product_uom_qty = qty
        return returned

    def test_second_return_demand(self):
        """1ra devolucion (2u) + 2da devolucion (3u): la 2da debe nacer con demanda 3, no 3 - 2."""
        order = self._new_order(qty=10)
        delivery = order.picking_ids
        self._validate(delivery)

        self._validate(self._return(delivery, qty=2))
        self.assertEqual(order.order_line.quantity_returned, 2.0)

        second = self._return(delivery, qty=3)
        self.assertEqual(second.move_ids.product_uom_qty, 3.0)

    def test_return_then_exchange(self):
        """Devolver 2u y cambiarlas: lo entregado baja y vuelve a subir."""
        order = self._new_order(qty=10)
        line = order.order_line
        delivery = order.picking_ids
        self._validate(delivery)

        returned = self._return(delivery, qty=2)
        self._validate(returned)
        self.assertEqual(line.qty_delivered, 8.0)
        self.assertEqual(line.quantity_returned, 2.0)

        exchange = self.env["stock.picking"].browse(returned.action_exchange()["res_id"])
        self.assertEqual(
            exchange.move_ids.product_uom_qty,
            2.0,
            "El cambio debe pedir 2u; el hack lo dejaba en 2 - quantity_returned.",
        )
        self._validate(exchange)
        self.assertEqual(line.qty_delivered, 10.0)
        self.assertEqual(line.delivery_status, "full")
