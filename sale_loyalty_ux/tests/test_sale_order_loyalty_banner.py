from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon
from odoo.fields import Command
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestSaleOrderLoyaltyRewardsBanner(TestSaleCouponCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sale_exception_installed = cls.env["sale.order"]._fields.get("ignore_exception")
        if sale_exception_installed:
            cls.env["exception.rule"].search([("active", "=", True)]).write({"active": False})
        cls.reward_banner_program = cls.env["loyalty.program"].create(
            {
                "name": "Reward reminder program",
                "company_id": cls.env.company.id,
                "program_type": "loyalty",
                "trigger": "auto",
                "applies_on": "future",
                "rule_ids": [
                    Command.create(
                        {
                            "product_ids": [Command.set([cls.product_A.id])],
                            "minimum_qty": 1,
                            "reward_point_amount": 1,
                            "reward_point_mode": "order",
                        }
                    )
                ],
                "reward_ids": [
                    Command.create(
                        {
                            "reward_type": "discount",
                            "discount_mode": "per_point",
                            "discount_applicability": "order",
                            "discount": 1,
                            "required_points": 1,
                        }
                    )
                ],
            }
        )

    def _create_order(self):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product_A.id,
                            "product_uom_qty": 1,
                            "price_unit": self.product_A.list_price,
                        }
                    )
                ],
            }
        )

    def test_banner_visible_when_rewards_are_available(self):
        order = self._create_order()
        order._update_programs_and_rewards()

        self.assertTrue(order.loyalty_rewards_banner_visible)

        claimable_rewards = order._get_claimable_rewards()
        coupon, rewards = next(iter(claimable_rewards.items()))
        order._apply_program_reward(rewards[:1], coupon)

        self.assertFalse(order.loyalty_rewards_banner_visible)

    def test_banner_hidden_on_confirmed_orders(self):
        order = self._create_order()
        order._update_programs_and_rewards()
        order.write({"state": "sale"})

        self.assertEqual(order.state, "sale")
        self.assertFalse(order.loyalty_rewards_banner_visible)
