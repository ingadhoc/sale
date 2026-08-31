from unittest.mock import patch

from odoo import Command
from odoo.tests.common import TransactionCase


class TestCancelRemaining(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
                "customer_rank": 1,
            }
        )

        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product",
                "type": "product",
                "list_price": 100.0,
            }
        )

        cls.sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_uom_qty": 10,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )

        cls.sale_order.action_confirm()

    def test_cancel_remaining_on_locked_order(self):
        """
        Test that button_cancel_remaining works on locked (done) sale orders
        without generating tracking messages in the chatter.
        """
        # Deliver part of the order
        picking = self.sale_order.picking_ids[0]
        for move in picking.move_ids:
            move.quantity = 5
        picking._action_done()

        # Lock the sale order
        self.sale_order.write({"state": "done"})
        self.assertEqual(self.sale_order.state, "done")

        # Count initial messages
        initial_message_count = len(self.sale_order.message_ids)

        # Cancel remaining quantities
        line = self.sale_order.order_line[0]
        line.button_cancel_remaining()

        # Verify the order is still locked
        self.assertEqual(self.sale_order.state, "done", "Order should remain locked after cancel remaining")

        # Verify the quantity was adjusted
        self.assertEqual(
            line.product_uom_qty, 5.0, "Product qty should be equal to qty_delivered after cancel remaining"
        )

        # Verify only one message was posted (the cancel remaining message, not the state changes)
        final_message_count = len(self.sale_order.message_ids)
        self.assertEqual(
            final_message_count,
            initial_message_count + 1,
            "Only one message should be added (cancel remaining), no state change messages",
        )

    def test_cancel_remaining_resets_printed_open_pickings(self):
        picking = self.sale_order.picking_ids[0]
        picking.printed = True

        line = self.sale_order.order_line[0]
        line.button_cancel_remaining()

        self.assertFalse(picking.printed, "Printed should be reset on open pickings before reducing qty")

    def test_cancel_remaining_relocks_order_on_error(self):
        self.sale_order.write({"state": "done"})
        self.assertTrue(self.sale_order.locked, "Order should be locked before testing relock safeguard")

        line = self.sale_order.order_line[0]
        with patch.object(type(self.sale_order), "message_post", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                line.button_cancel_remaining()

        self.assertTrue(self.sale_order.locked, "Order should be relocked even if cancel remaining fails")

    # --- Casos de 2 pasos (pick_ship): no deben generar contra-entregas (ticket 118147) ---

    def _2step_warehouse(self):
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)
        warehouse.delivery_steps = "pick_ship"
        return warehouse

    def _add_stock(self, product, warehouse, qty):
        self.env["stock.quant"]._update_available_quantity(product, warehouse.lot_stock_id, qty)

    def _2step_order(self, qty=10.0):
        warehouse = self._2step_warehouse()
        self._add_stock(self.product, warehouse, qty)
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": warehouse.id,
                "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": qty})],
            }
        )
        order.action_confirm()
        return order

    @staticmethod
    def _validate(picking, qty=None):
        for move in picking.move_ids.filtered(lambda m: m.state not in ("done", "cancel")):
            move._action_assign()
            do_qty = move.product_uom_qty if qty is None else min(qty, move.product_uom_qty)
            if move.move_line_ids:
                move.move_line_ids[0].quantity = do_qty
            move.picked = True
        picking._action_done()

    def _assert_no_contra_entrega(self, order):
        moves = order.order_line.move_ids
        bad = moves.filtered(lambda m: m.state != "cancel" and (m.to_refund or m.product_uom_qty < 0))
        self.assertFalse(
            bad,
            "Cancel remaining no debe dejar moves to_refund/negativos vivos (contra-entregas): %s" % bad.ids,
        )
        incoming = order.picking_ids.filtered(lambda p: p.state != "cancel" and p.picking_type_id.code == "incoming")
        self.assertFalse(incoming, "Cancel remaining no debe crear pickings de entrada (contra-entregas)")

    def test_cancel_remaining_pick_ship_pick_done(self):
        """PICK validado (stock en Salida) + OUT pendiente: cancelar remanente no
        debe generar el traslado reverso Salida->Existencias."""
        order = self._2step_order(qty=10.0)
        pick = order.picking_ids.filtered(lambda p: p.picking_type_id.code == "internal")
        self._validate(pick)
        done_moves_before = order.order_line.move_ids.filtered(lambda m: m.state == "done")

        order.order_line.button_cancel_remaining()

        self._assert_no_contra_entrega(order)
        self.assertTrue(
            all(m.state == "done" for m in done_moves_before),
            "Los moves ya entregados (done) no deben tocarse",
        )
        out = order.picking_ids.filtered(lambda p: p.picking_type_id.code == "outgoing")
        self.assertTrue(all(m.state == "cancel" for m in out.move_ids), "El OUT pendiente debe quedar cancelado")

    def test_cancel_remaining_pick_ship_partial_backorder(self):
        """Entrega parcial del PICK (backorder pendiente) + OUT pendiente:
        cancelar remanente no debe generar contra-entregas aunque sobre la
        fracción ya pickeada a Salida."""
        order = self._2step_order(qty=10.0)
        pick = order.picking_ids.filtered(lambda p: p.picking_type_id.code == "internal")
        self._validate(pick, qty=6.0)  # genera backorder por 4

        order.order_line.button_cancel_remaining()

        self._assert_no_contra_entrega(order)
        line = order.order_line
        self.assertEqual(line.delivery_status, "full", "La línea debe quedar como entregada tras cancelar el remanente")
