from odoo.tests import TransactionCase


class TestReturnOfReturn(TransactionCase):
    """Devolver una devolución ligada a una OV advierte pero deja continuar.

    Reenviar al cliente mercadería ya devuelta mediante una cadena de
    devoluciones puede dejar la orden de venta inconsistente (cantidades
    entregadas / estado de facturación). En vez de bloquear, se pide
    confirmación al usuario y, si confirma, se crea la devolución igual.
    Ver tickets 119865 y 119975.
    """

    def setUp(self):
        super().setUp()
        # Entrega en 1 paso para un escenario determinista (el guardrail es
        # independiente de la cantidad de pasos: chequea topología del picking).
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)
        warehouse.delivery_steps = "ship_only"

        self.partner = self.env["res.partner"].create({"name": "Test Partner", "customer_rank": 1})
        self.product = self.env["product.product"].create(
            {
                "name": "Test almacenable",
                "type": "consu",
                "is_storable": True,
                "invoice_policy": "order",
                "list_price": 100.0,
            }
        )
        if self.env["sale.order"]._fields.get("ignore_exception"):
            self.env["exception.rule"].search([("active", "=", True)]).write({"active": False})

        self.sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": warehouse.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 10.0, "price_unit": 100.0})],
            }
        )
        self.sale_order.action_confirm()
        self.delivery = self.sale_order.picking_ids
        self._validate(self.delivery)

    def _validate(self, picking):
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.move_line_ids.unlink()
            move.quantity = move.product_uom_qty
            move.picked = True
        picking._action_done()

    def _make_return_wizard(self, picking, to_refund=True, quantity=10.0):
        wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=picking.id, active_ids=picking.ids, active_model="stock.picking")
            .create({})
        )
        for line in wizard.product_return_moves:
            line.to_refund = to_refund
            line.quantity = quantity
        return wizard

    def _make_return(self, picking, to_refund=True, quantity=10.0):
        wizard = self._make_return_wizard(picking, to_refund=to_refund, quantity=quantity)
        action = wizard.action_create_returns()
        return self.env["stock.picking"].browse(action["res_id"])

    def test_first_return_is_allowed(self):
        """La primera devolución (sobre la entrega original) no advierte."""
        returned = self._make_return(self.delivery, to_refund=True)
        self.assertEqual(returned.return_id, self.delivery)
        self.assertTrue(returned.sale_id)

    def test_return_of_return_to_refund_warns_but_continues(self):
        returned = self._make_return(self.delivery, to_refund=True)
        self._validate(returned)
        self._assert_warns_then_creates(returned, to_refund=True)

    def test_return_of_return_without_refund_warns_but_continues(self):
        returned = self._make_return(self.delivery, to_refund=False)
        self._validate(returned)
        self._assert_warns_then_creates(returned, to_refund=False)

    def _assert_warns_then_creates(self, returned, to_refund):
        """No se bloquea: primero advierte (reabre el wizard), luego crea."""
        wizard = self._make_return_wizard(returned, to_refund=to_refund, quantity=7.0)
        pickings_before = self.sale_order.picking_ids

        # No crea la devolución todavía: reabre el mismo wizard mostrando la
        # advertencia (sin modelo nuevo, vía contexto).
        action = wizard.action_create_returns()
        self.assertEqual(action["res_model"], "stock.return.picking")
        self.assertEqual(action["res_id"], wizard.id)
        self.assertTrue(action["context"].get("show_return_of_return_warning"))
        self.assertEqual(self.sale_order.picking_ids, pickings_before)

        # "Continuar igual" reentra con el flag de skip y crea la devolución.
        confirm_action = wizard.with_context(skip_return_of_sale_return_check=True).action_create_returns()
        new_picking = self.env["stock.picking"].browse(confirm_action["res_id"])
        self.assertEqual(new_picking.return_id, returned)
        self.assertNotIn(new_picking, pickings_before)

    def test_exchange_from_original_delivery_is_allowed(self):
        """El flujo de exchange (action_create_exchanges) no debe advertir."""
        wizard = (
            self.env["stock.return.picking"]
            .with_context(
                active_id=self.delivery.id,
                active_ids=self.delivery.ids,
                active_model="stock.picking",
            )
            .create({})
        )
        for line in wizard.product_return_moves:
            line.to_refund = False
            line.quantity = line.move_id.quantity
        wizard.action_create_exchanges()
        self.assertGreaterEqual(len(self.sale_order.picking_ids), 3)
