from lxml import etree
from odoo import Command
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestSaleMarginUx(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context={**cls.env.context, "tracking_disable": True, "mail_notrack": True, "mail_create_nolog": True}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Sale Margin UX Customer"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Sale Margin UX Product",
                "type": "consu",
                "list_price": 100.0,
                "standard_price": 10.0,
            }
        )
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [Command.create({"product_id": cls.product.id, "product_uom_qty": 2.0})],
            }
        )
        cls.line = cls.order.order_line

    def test_update_prices_recomputes_the_cost_of_the_lines(self):
        self.assertEqual(self.line.purchase_price, 10.0)
        self.product.standard_price = 25.0
        # changing the product cost alone does not touch the lines already created
        self.assertEqual(self.line.purchase_price, 10.0)

        self.order.action_update_prices()

        self.assertEqual(self.line.purchase_price, 25.0)

    def test_update_prices_recomputes_the_margin_with_the_new_cost(self):
        self.product.standard_price = 40.0

        self.order.action_update_prices()

        self.assertEqual(self.line.purchase_price, 40.0)
        self.assertEqual(self.line.margin, self.line.price_subtotal - 40.0 * 2.0)

    def test_update_prices_returns_true(self):
        self.assertTrue(self.order.action_update_prices())

    def test_lines_list_view_shows_cost_and_margin_columns(self):
        view = self.env.ref("sale_ux.sale_order_line_usability_tree")
        user = new_test_user(self.env, login="sale_margin_ux_user", groups="sales_team.group_sale_salesman")

        arch = self.env["sale.order.line"].with_user(user).get_view(view.id, "list")["arch"]

        tree = etree.fromstring(arch)
        for name in ("purchase_price", "margin", "margin_percent"):
            nodes = tree.xpath(f"//field[@name='{name}']")
            self.assertEqual(len(nodes), 1, f"{name} must be in the lines list view")
            self.assertEqual(nodes[0].get("optional"), "hide", f"{name} must be optional and hidden by default")
