import odoo
from odoo import Command
from odoo.addons.pos_mrp.tests.common import CommonPosMrpTest


@odoo.tests.tagged("post_install", "-at_install")
class TestPosMrpUx(CommonPosMrpTest):
    def test_kit_and_lot_tracked_component_in_the_same_order(self):
        component = self.env["product.template"].create(
            {
                "name": "Lot tracked component",
                "available_in_pos": True,
                "list_price": 5.0,
                "tracking": "lot",
                "type": "consu",
                "is_storable": True,
            }
        )
        kit = self.env["product.template"].create(
            {
                "name": "Kit of six",
                "available_in_pos": True,
                "list_price": 25.0,
                "type": "consu",
                "is_storable": True,
            }
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": component.product_variant_id.id,
                            "product_qty": 6.0,
                        }
                    ),
                ],
            }
        )

        order, _ = self.create_backend_pos_order(
            {
                "order_data": {"partner_id": self.partner.id},
                "line_data": [
                    {"product_id": kit.product_variant_id.id, "qty": 1},
                    {
                        "product_id": component.product_variant_id.id,
                        "qty": 1,
                        "pack_lot_ids": [Command.create({"lot_name": "lot_one"})],
                    },
                    {
                        "product_id": component.product_variant_id.id,
                        "qty": 1,
                        "pack_lot_ids": [Command.create({"lot_name": "lot_one"})],
                    },
                ],
                "payment_data": [{"payment_method_id": self.cash_payment_method.id}],
            }
        )

        kit_move = order.picking_ids.move_ids.filtered("bom_line_id")
        self.assertEqual(len(kit_move), 1)
        self.assertEqual(kit_move.product_uom_qty, 6.0)
        self.assertEqual(kit_move.quantity, 6.0)
