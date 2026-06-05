from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import SaleGatheringIndexCommon


@tagged("post_install", "-at_install")
class TestSaleGatheringIndexOrderLine(SaleGatheringIndexCommon):
    def test_cannot_add_same_product_twice_after_gathering_confirmation(self):
        order = self._confirm_gathering_order()

        with self.assertRaises(UserError):
            self.env["sale.order.line"].create(
                {
                    "order_id": order.id,
                    "product_id": self.product_a.id,
                    "product_uom_qty": 0.0,
                    "price_unit": 100.0,
                    "tax_ids": [Command.clear()],
                }
            )

    def test_cannot_increase_quantity_of_redeemed_line(self):
        order = self._confirm_gathering_order(
            lines=[
                Command.create(
                    {
                        "product_id": self.product_a.id,
                        "product_uom_qty": 2.0,
                        "price_unit": 100.0,
                        "tax_ids": [Command.clear()],
                    }
                ),
                Command.create(
                    {
                        "product_id": self.product_b.id,
                        "product_uom_qty": 0.0,
                        "price_unit": 120.0,
                        "tax_ids": [Command.clear()],
                    }
                ),
            ]
        )
        added_line = order.order_line.filtered(
            lambda line: line.product_id == self.product_b and line.initial_qty_gathered == 0
        )

        with self.assertRaises(UserError):
            added_line.write({"product_uom_qty": 1.0})

    def test_cannot_change_description_of_regular_gathering_lines(self):
        order = self._confirm_gathering_order(
            lines=[
                Command.create(
                    {
                        "product_id": self.product_a.id,
                        "product_uom_qty": 2.0,
                        "price_unit": 100.0,
                        "tax_ids": [Command.clear()],
                    }
                ),
                Command.create(
                    {
                        "product_id": self.product_b.id,
                        "product_uom_qty": 0.0,
                        "price_unit": 120.0,
                        "tax_ids": [Command.clear()],
                    }
                ),
            ]
        )
        regular_lines = order.order_line.filtered(lambda line: not line.is_downpayment and not line.display_type)

        with self.assertRaises(UserError):
            regular_lines.write({"name": "Updated description"})
