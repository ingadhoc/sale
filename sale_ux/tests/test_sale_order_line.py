from odoo import Command
from odoo.tests import tagged

from .common import SaleUxCommon


@tagged("post_install", "-at_install")
class TestSaleOrderLine(SaleUxCommon):
    def test_action_sale_history_filters_by_product_and_partner(self):
        order = self._create_sale_order()
        line = order.order_line[0]

        action = line.action_sale_history()

        self.assertEqual(
            action["domain"],
            [("state", "in", ["sale", "done"]), ("product_id", "=", line.product_id.id)],
        )
        self.assertEqual(action["context"]["search_default_partner_id"], 1)
        self.assertIn(line.product_id.display_name, action["display_name"])

    def test_get_protected_fields_includes_discount(self):
        order = self._create_sale_order()

        protected_fields = order.order_line._get_protected_fields()

        self.assertIn("discount", protected_fields)

    def test_line_without_product_is_supported(self):
        """Odoo 20 allows lines with only a description and a unit of measure."""
        order = self._create_sale_order(
            order_line=[
                Command.create(
                    {
                        "name": "Line without product",
                        "product_uom_qty": 1.0,
                        "price_unit": 50.0,
                        "product_uom_id": self.product_uom_unit.id,
                    }
                )
            ]
        )
        line = order.order_line

        self.assertFalse(line.product_id)
        self.assertEqual(line.product_uom_id, self.product_uom_unit)
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_allowed_uoms_of_lines_without_product(self):
        """Sections, notes and lines without product must not break reading allowed_uom_ids."""
        order = self._create_sale_order(
            order_line=[
                Command.create({"display_type": "line_section", "name": "Section"}),
                Command.create({"display_type": "line_note", "name": "Note"}),
                Command.create(
                    {
                        "name": "Line without product",
                        "product_uom_qty": 1.0,
                        "price_unit": 50.0,
                        "product_uom_id": self.product_uom_unit.id,
                    }
                ),
                Command.create({"product_id": self.product.id, "product_uom_qty": 1.0}),
            ]
        )
        order.invalidate_recordset()

        for line in order.order_line:
            if line.product_id:
                self.assertTrue(line.allowed_uom_ids)
            else:
                self.assertFalse(line.allowed_uom_ids)
        # what the form reads when opening the order
        order.web_read({"order_line": {"fields": {"allowed_uom_ids": {}}}})

    def test_confirmed_order_keeps_manual_discount(self):
        order = self._create_sale_order()
        order.action_confirm()
        line = order.order_line[0]

        line.discount = 10.0
        line._compute_discount()

        self.assertEqual(line.discount, 10.0)
