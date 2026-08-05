from odoo import Command
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

    def test_index_is_zero_right_after_confirmation_with_agreed_price(self):
        """Confirming at a price below the list price is a commercial discount, not a variation."""
        order = self._confirm_gathering_order(
            lines=[
                Command.create(
                    {
                        "product_id": self.product_a.id,
                        "product_uom_qty": 2.0,
                        "price_unit": 80.0,
                        "tax_ids": [Command.clear()],
                    }
                )
            ]
        )

        self.assertAlmostEqual(order.order_line.gathering_base_price_unit, 100.0)
        self.assertAlmostEqual(order.gathering_amount_with_taxes, 160.0)
        self.assertAlmostEqual(order.indexed_gathering_amount, 160.0)
        self.assertAlmostEqual(order.index, 0.0)
        self.assertAlmostEqual(order.coef, 1.0)

    def test_index_only_reflects_price_variation_after_confirmation(self):
        order = self._confirm_gathering_order(
            lines=[
                Command.create(
                    {
                        "product_id": self.product_a.id,
                        "product_uom_qty": 2.0,
                        "price_unit": 80.0,
                        "tax_ids": [Command.clear()],
                    }
                )
            ]
        )
        self.product_a.list_price = 130.0

        order._compute_indexed_gathering_amount()
        order._compute_index()

        # +30% on the list price, applied over the agreed price: 80 * 1.3 * 2 units.
        self.assertAlmostEqual(order.indexed_gathering_amount, 208.0)
        self.assertAlmostEqual(order.index, 0.3)
        self.assertAlmostEqual(order.coef, 1.3)

    def test_indexed_amounts_recompute_over_several_orders(self):
        """Changing a list price recomputes every gathering order holding that product at once."""
        orders = self._confirm_gathering_order() + self._confirm_gathering_order()

        self.product_a.list_price = 200.0
        self.env.flush_all()

        self.assertEqual(orders.mapped("index"), [1.0, 1.0])
        self.assertEqual(orders.mapped("indexed_gathering_amount"), [400.0, 400.0])

    def test_indexed_withdrawn_amount_when_fully_withdrawn(self):
        order = self._confirm_gathering_order()
        self._create_and_pay_gathering_downpayment(order, amount=200.0)

        order.order_line.filtered(lambda line: not line.is_downpayment).product_uom_qty = 2.0

        self.assertAlmostEqual(order.gathering_balance, 0.0)
        self.assertAlmostEqual(order.withdrawn_amount, 200.0)
        self.assertAlmostEqual(order.gathering_balance_indexed, 0.0)
        self.assertAlmostEqual(order.indexed_withdrawn_amount, 200.0)

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
