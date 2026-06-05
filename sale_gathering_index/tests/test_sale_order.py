from odoo.tests import tagged

from .common import SaleGatheringIndexCommon


@tagged("post_install", "-at_install")
class TestSaleGatheringIndexOrder(SaleGatheringIndexCommon):
    def test_index_and_coef_are_computed_from_current_prices(self):
        order = self._confirm_gathering_order()
        self.product_a.list_price = 200.0

        order._compute_indexed_gathering_amount()
        order._compute_index()

        self.assertAlmostEqual(order.gathering_amount_with_taxes, 200.0)
        self.assertAlmostEqual(order.indexed_gathering_amount, 400.0)
        self.assertAlmostEqual(order.index, 1.0)
        self.assertAlmostEqual(order.coef, 2.0)

    def test_indexed_balances_after_partial_withdrawal(self):
        order = self._confirm_gathering_order()
        self._create_and_pay_gathering_downpayment(order, amount=250.0)

        gathering_line = order.order_line.filtered(lambda line: not line.is_downpayment)
        gathering_line.write({"product_uom_qty": 1.0})
        self.product_a.list_price = 200.0

        order._compute_gathering_balance()
        order._compute_indexed_gathering_amount()
        order._compute_index()
        order._compute_gathering_balance_indexed()
        order._compute_indexed_withdrawn_amount()

        self.assertAlmostEqual(order.gathering_balance, 150.0)
        self.assertAlmostEqual(order.indexed_gathering_amount, 400.0)
        self.assertAlmostEqual(order.index, 1.0)
        self.assertAlmostEqual(order.gathering_balance_indexed, 300.0)
        self.assertAlmostEqual(order.indexed_withdrawn_amount, 100.0)
