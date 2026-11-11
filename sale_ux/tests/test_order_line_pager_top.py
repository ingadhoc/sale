from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestOrderLinePagerTop(HttpCase):
    """The core puts the pager of the order lines below them. We also show it above, and both move the same page.
    If a new Odoo changes the field this extends, this tour is what breaks."""

    def test_pager_is_also_above_the_order_lines(self):
        partner = self.env["res.partner"].create({"name": "Pager top test partner"})
        product = self.env["product.product"].create({"name": "Pager top test product"})
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [(0, 0, {"product_id": product.id, "product_uom_qty": 1}) for _i in range(45)],
            }
        )

        self.start_tour(
            f"/odoo/action-sale.action_orders/{order.id}", "sale_ux_order_line_pager_top_tour", login="admin"
        )
