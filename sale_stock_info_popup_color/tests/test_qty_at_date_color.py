from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestQtyAtDateColor(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.partner = cls.env["res.partner"].create({"name": "Popup Color Customer"})
        cls.product_incoming, cls.product_on_hand = cls.env["product.product"].create(
            [
                {"name": "Popup Color Incoming", "is_storable": True},
                {"name": "Popup Color On Hand", "is_storable": True},
            ]
        )
        cls.env["stock.quant"]._update_available_quantity(cls.product_on_hand, cls.warehouse.lot_stock_id, 10)
        receipt = cls.env["stock.picking"].create(
            {
                "picking_type_id": cls.warehouse.in_type_id.id,
                "partner_id": cls.partner.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": cls.product_incoming.id,
                            "product_uom_qty": 10,
                            "location_id": cls.env.ref("stock.stock_location_suppliers").id,
                            "location_dest_id": cls.warehouse.lot_stock_id.id,
                        }
                    )
                ],
            }
        )
        receipt.action_confirm()
        cls.sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "warehouse_id": cls.warehouse.id,
                "order_line": [
                    Command.create({"product_id": cls.product_incoming.id, "product_uom_qty": 5}),
                    Command.create({"product_id": cls.product_on_hand.id, "product_uom_qty": 5}),
                ],
            }
        )

    def test_icon_red_without_free_qty_today(self):
        line_incoming, line_on_hand = self.sale_order.order_line
        # The forecast covers the incoming line, so the core alone would not flag it
        self.assertGreaterEqual(line_incoming.virtual_available_at_date, line_incoming.qty_to_deliver)
        self.assertLess(line_incoming.free_qty_today, line_incoming.qty_to_deliver)
        self.assertGreaterEqual(line_on_hand.free_qty_today, line_on_hand.qty_to_deliver)
        self.start_tour(
            f"/odoo/sales/{self.sale_order.id}",
            "sale_stock_info_popup_color_tour",
            login="admin",
        )
