##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestSaleOrderTypePickingType(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.company.id)], limit=1)
        cls.other_warehouse = cls.env["stock.warehouse"].create(
            {"name": "Second warehouse", "code": "WH2", "company_id": cls.company.id}
        )
        cls.second_picking_type = cls.env["stock.picking.type"].create(
            {
                "name": "Delivery second book",
                "code": "outgoing",
                "sequence_code": "OUT2",
                "warehouse_id": cls.warehouse.id,
                "company_id": cls.company.id,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test partner sale order type"})
        cls.product = cls.env["product.product"].create(
            {"name": "Test product sale order type", "type": "consu", "is_storable": True}
        )
        cls.sale_type = cls.env["sale.order.type"].create(
            {
                "name": "Type with operation type",
                "company_id": cls.company.id,
                "warehouse_id": cls.warehouse.id,
                "picking_type_id": cls.second_picking_type.id,
            }
        )

    def _create_order(self, sale_type):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "company_id": self.company.id,
                "type_id": sale_type.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 1.0}),
                ],
            }
        )
        # launch the procurement without action_confirm, that other modules hook into,
        # and without the exception rules of base_exception on the test partner
        order = order.with_context(check_exception=False)
        order.write({"state": "sale"})
        order.order_line._action_launch_stock_rule()
        return order

    def test_01_delivery_uses_the_type_picking_type(self):
        order = self._create_order(self.sale_type)
        moves = order.order_line.move_ids
        self.assertTrue(moves)
        self.assertEqual(moves.picking_type_id, self.second_picking_type)
        self.assertEqual(moves.picking_id.picking_type_id, self.second_picking_type)

    def test_02_without_picking_type_keeps_the_warehouse_one(self):
        sale_type = self.sale_type.copy({"name": "Type without operation type", "picking_type_id": False})
        order = self._create_order(sale_type)
        moves = order.order_line.move_ids
        self.assertTrue(moves)
        self.assertEqual(moves.picking_type_id, self.warehouse.out_type_id)

    def test_03_changing_the_warehouse_clears_the_picking_type(self):
        self.sale_type.warehouse_id = self.other_warehouse
        self.assertFalse(self.sale_type.picking_type_id)

    def test_04_picking_type_of_another_warehouse_is_not_allowed(self):
        with self.assertRaises(ValidationError):
            self.sale_type.write(
                {
                    "warehouse_id": self.other_warehouse.id,
                    "picking_type_id": self.second_picking_type.id,
                }
            )

    def test_05_two_steps_delivery_only_changes_the_last_step(self):
        self.warehouse.delivery_steps = "pick_ship"
        self.env["stock.quant"]._update_available_quantity(self.product, self.warehouse.lot_stock_id, 10)
        order = self._create_order(self.sale_type)
        pick = order.picking_ids
        self.assertEqual(pick.picking_type_id, self.warehouse.pick_type_id)
        pick.action_assign()
        pick.move_ids.quantity = 1
        pick.button_validate()
        delivery = order.picking_ids - pick
        self.assertEqual(delivery.picking_type_id, self.second_picking_type)
