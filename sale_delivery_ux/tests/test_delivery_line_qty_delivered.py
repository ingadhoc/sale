##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeliveryLineQtyDelivered(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test storable product",
                "type": "consu",
                "is_storable": True,
            }
        )
        cls.env["stock.quant"]._update_available_quantity(cls.product, cls.warehouse.lot_stock_id, 100)
        cls.carrier = cls.env["delivery.carrier"].create(
            {
                "name": "Test fixed carrier",
                "delivery_type": "fixed",
                "fixed_price": 100.0,
                "product_id": cls.env.ref("delivery.product_product_delivery").id,
            }
        )
        # fixed_price lives on the delivery product, so each carrier needs its own
        cls.free_carrier = cls.env["delivery.carrier"].create(
            {
                "name": "Test free carrier",
                "delivery_type": "fixed",
                "fixed_price": 0.0,
                "product_id": cls.env.ref("delivery.product_product_delivery")
                .copy({"name": "Test free delivery product"})
                .id,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test customer"})
        # active exception rules keep the order in draft on confirmation, so no picking is created
        if cls.env["sale.order"]._fields.get("ignore_exception"):
            cls.env["exception.rule"].sudo().search([("active", "=", True)]).write({"active": False})

    def _create_sale_order(self, carrier=None):
        carrier = carrier or self.carrier
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 5})],
            }
        )
        order.set_delivery_line(carrier, carrier.fixed_price)
        order.action_confirm()
        self.assertTrue(order.picking_ids, "the order was confirmed without creating any picking")
        return order

    def _validate(self, picking):
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        picking.button_validate()

    def _delivery_line(self, order):
        return order.order_line.filtered("is_delivery")

    def test_three_steps_delivery_marked_on_last_step(self):
        self.warehouse.delivery_steps = "pick_pack_ship"
        order = self._create_sale_order()
        delivery_line = self._delivery_line(order)

        self._validate(order.picking_ids)
        self.assertEqual(delivery_line.qty_delivered, 0.0)
        self.assertEqual(order.delivery_status, "started")

        self._validate(order.picking_ids.filtered(lambda p: p.state != "done"))
        self.assertEqual(delivery_line.qty_delivered, 0.0)
        self.assertEqual(order.delivery_status, "started")

        out_picking = order.picking_ids.filtered(lambda p: p.state != "done")
        self.assertTrue(any(move._is_outgoing() for move in out_picking.move_ids))
        self._validate(out_picking)
        self.assertEqual(delivery_line.qty_delivered, 1.0)
        self.assertEqual(order.delivery_status, "full")

    def test_one_step_delivery_marked_on_validation(self):
        self.warehouse.delivery_steps = "ship_only"
        order = self._create_sale_order()

        self._validate(order.picking_ids)
        self.assertEqual(self._delivery_line(order).qty_delivered, 1.0)
        self.assertEqual(order.delivery_status, "full")

    def test_internal_picking_does_not_mark_another_order(self):
        self.warehouse.delivery_steps = "pick_pack_ship"
        internal_order = self._create_sale_order()
        self.warehouse.delivery_steps = "ship_only"
        outgoing_order = self._create_sale_order()

        internal_picking = internal_order.picking_ids
        outgoing_picking = outgoing_order.picking_ids
        for picking in internal_picking | outgoing_picking:
            picking.action_assign()
            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
                move.picked = True
        (internal_picking | outgoing_picking)._action_done()

        self.assertEqual(self._delivery_line(internal_order).qty_delivered, 0.0)
        self.assertEqual(self._delivery_line(outgoing_order).qty_delivered, 1.0)

    def test_zero_price_delivery_line_has_no_qty(self):
        self.warehouse.delivery_steps = "ship_only"
        order = self._create_sale_order(self.free_carrier)
        delivery_line = self._delivery_line(order)

        self.assertEqual(delivery_line.product_uom_qty, 0.0)
        self.assertEqual(delivery_line.qty_to_invoice, 0.0)

    def test_zero_price_delivery_line_on_locked_order(self):
        self.warehouse.delivery_steps = "ship_only"
        order = self._create_sale_order()
        order.locked = True

        # protected fields keep a locked order from changing the quantity, and
        # the module lifts that guard for the zero cost delivery line
        order.set_delivery_line(self.free_carrier, self.free_carrier.fixed_price)

        self.assertEqual(self._delivery_line(order).product_uom_qty, 0.0)
