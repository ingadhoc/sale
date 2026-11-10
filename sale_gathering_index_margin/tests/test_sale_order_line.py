from odoo.addons.sale_gathering_index.tests.common import SaleGatheringIndexCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestSaleGatheringIndexMargin(SaleGatheringIndexCommon):
    """The cost of a redeemed line is divided by the coef, so the margin is comparable.

    The price of a redeemed product already comes divided by the coef (`sale_gathering_index`),
    so leaving the cost at its current value would show a margin that is not the one the
    business made. The module only acts while the line is being edited, on the virtual record
    the interface works with, and the value it computes is what gets stored.
    """

    def _redeemed_line(self, order):
        return self.env["sale.order.line"].new(
            {
                "order_id": order.id,
                "product_id": self.product_b.id,
                "product_uom_qty": 1.0,
            }
        )

    def test_the_cost_of_a_redeemed_line_follows_the_coef(self):
        order = self._confirm_gathering_order()
        self.product_a.list_price = 200.0

        self.assertAlmostEqual(order.coef, 2.0, msg="El acopio tiene que haber duplicado su índice")
        self.assertAlmostEqual(self._redeemed_line(order).purchase_price, 35.0)

    def test_without_variation_the_cost_is_the_plain_one(self):
        order = self._confirm_gathering_order()

        self.assertAlmostEqual(order.coef, 1.0)
        self.assertAlmostEqual(self._redeemed_line(order).purchase_price, 70.0)

    def test_a_gathered_line_keeps_its_own_cost(self):
        """The adjustment is for what is redeemed, not for what was gathered."""
        order = self._confirm_gathering_order()
        self.product_a.list_price = 200.0

        gathered = order.order_line.filtered(lambda line: line.initial_qty_gathered > 0)

        self.assertAlmostEqual(gathered.purchase_price, 50.0)
