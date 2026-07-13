from odoo.addons.sale_product_pack.tests.common import TestSaleProductPackBase


class TestSaleStockProductPackUx(TestSaleProductPackBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pack.type = "consu"
        cls.component1.is_storable = True
        cls.component2.is_storable = True
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        # One-step delivery: the test assumes a single outgoing picking.
        cls.warehouse.delivery_steps = "ship_only"
        cls.env["stock.quant"]._update_available_quantity(cls.component1, cls.warehouse.lot_stock_id, 20)
        cls.env["stock.quant"]._update_available_quantity(cls.component2, cls.warehouse.lot_stock_id, 20)

    def _create_return_moves(self, delivery_moves, qty_by_product):
        # Return moves built by hand: the wizard depends on the warehouse route.
        return_picking = self.env["stock.picking"].create(
            {
                "picking_type_id": delivery_moves[:1].picking_id.picking_type_id.id,
                "location_id": delivery_moves[:1].location_dest_id.id,
                "location_dest_id": delivery_moves[:1].location_id.id,
            }
        )
        for move in delivery_moves:
            qty = qty_by_product.get(move.product_id, 0.0)
            if not qty:
                continue
            self.env["stock.move"].create(
                {
                    "product_id": move.product_id.id,
                    "product_uom_qty": qty,
                    "quantity": qty,
                    "product_uom": move.product_uom.id,
                    "picking_id": return_picking.id,
                    "location_id": move.location_dest_id.id,
                    "location_dest_id": move.location_id.id,
                    "sale_line_id": move.sale_line_id.id,
                    "origin_returned_move_id": move.id,
                    "to_refund": True,
                    "state": "done",
                    "picked": True,
                }
            )
        return return_picking

    def test_quantity_returned_pack_after_component_return(self):
        """Returning a pack's components must update the pack line's own
        'quantity_returned', with no forced recompute."""
        pack_line = self._add_so_line()
        pack_line.product_uom_qty = 2
        sale = self.sale_order
        # sale_exception can turn action_confirm() into a no-op.
        if "ignore_exception" in sale._fields:
            sale.ignore_exception = True
        sale.action_confirm()
        self.assertEqual(sale.state, "sale", "action_confirm did not confirm the order.")
        picking = sale.picking_ids
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.move_ids.picked = True
        picking.button_validate()
        self.assertEqual(
            picking.state,
            "done",
            "Delivery picking did not complete (button_validate likely "
            "returned a wizard action instead of validating directly).",
        )

        self.assertEqual(pack_line.quantity_returned, 0.0)

        # Return exactly 1 pack's worth of both components (proportional).
        delivery_moves = picking.move_ids.filtered(lambda m: m.state == "done")
        self.assertTrue(delivery_moves, "No completed delivery moves found to return.")
        self._create_return_moves(delivery_moves, {self.component1: 2.0, self.component2: 1.0})

        # No explicit invalidate/recompute call here: this must reflect the
        # return through normal field dependency tracking alone.
        self.assertEqual(pack_line.quantity_returned, 1.0)
