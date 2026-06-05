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
