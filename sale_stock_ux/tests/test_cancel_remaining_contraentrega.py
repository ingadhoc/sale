from odoo.tests import TransactionCase


class TestCancelRemainingContraentrega(TransactionCase):
    """Regresión ticket 121400.

    Al cancelar el remanente de una línea NO entregada cuya salida fue reservada
    desde una sub-ubicación distinta al origen nominal de la regla de stock, NO
    debe generarse una contraentrega (movimiento inverso / picking de entrada
    fantasma) ni dejar el movimiento de salida huérfano comprometiendo stock.
    """

    def setUp(self):
        super().setUp()
        self.product = self.env["product.product"].create(
            {"name": "Test Product 121400", "list_price": 100.0, "type": "consu"}
        )
        self.partner = self.env["res.partner"].create({"name": "Test Partner 121400", "customer_rank": 1})

        # Desactivar reglas de excepción si el módulo está instalado (evita error en runbot)
        if self.env["sale.order"]._fields.get("ignore_exception"):
            self.env["exception.rule"].search([("active", "=", True)]).write({"active": False})

    def test_cancel_remaining_no_contraentrega_from_sublocation(self):
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)

        # Sub-ubicación bajo el stock del depósito (simula Caballito/Gargano de vreme)
        sub_location = self.env["stock.location"].create(
            {
                "name": "Sub Stock 121400",
                "usage": "internal",
                "location_id": warehouse.lot_stock_id.id,
            }
        )

        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 10, "price_unit": 100.0})],
            }
        )
        sale_order.action_confirm()

        line = sale_order.order_line
        out_move = line.move_ids
        self.assertEqual(len(out_move), 1)
        self.assertNotIn(out_move.state, ("done", "cancel"))

        # Gatillo del bug: la salida tiene como origen una sub-ubicación distinta
        # al origen nominal de la regla (warehouse.lot_stock_id). Eso hace que el
        # movimiento negativo del recálculo no se fusione con el move original.
        out_move.write({"location_id": sub_location.id})

        # Cancelar remanente (nada entregado)
        line.with_context(cancel_from_order=True).button_cancel_remaining()

        # 1) La línea baja a lo entregado (0)
        self.assertEqual(line.product_uom_qty, 0.0)
        # 2) El movimiento de salida quedó cancelado (no huérfano en 'confirmed')
        self.assertEqual(out_move.state, "cancel")
        # 3) NO se generó contraentrega: ningún picking de entrada en la orden
        incoming = sale_order.picking_ids.filtered(lambda p: p.picking_type_code == "incoming")
        self.assertFalse(incoming, "No debe generarse una contraentrega (picking de entrada)")
        # 4) NO hay movimientos vivos saliendo del cliente (el move inverso fantasma)
        phantom = line.move_ids.filtered(lambda m: m.state != "cancel" and m.location_id.usage == "customer")
        self.assertFalse(phantom, "No debe existir un movimiento inverso (contraentrega)")
