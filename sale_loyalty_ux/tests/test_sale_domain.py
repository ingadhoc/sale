from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon
from odoo.fields import Command, Domain
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestLoyaltyProgramSaleDomain(TestSaleCouponCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sale_exception_installed = cls.env["sale.order"]._fields.get("ignore_exception")
        if sale_exception_installed:
            cls.env["exception.rule"].search([("active", "=", True)]).write({"active": False})
        cls.other_partner = cls.env["res.partner"].create({"name": "Partner outside the sales domain"})
        cls.program = cls.env["loyalty.program"].create(
            {
                "name": "Sales domain program",
                "company_id": cls.env.company.id,
                "program_type": "promotion",
                "trigger": "auto",
                "applies_on": "current",
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
                            "discount_mode": "percent",
                            "discount_applicability": "order",
                            "discount": 10,
                        }
                    )
                ],
            }
        )

    def _create_order(self, partner=None):
        return self.env["sale.order"].create(
            {
                "partner_id": (partner or self.partner).id,
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

    def _check(self, order):
        return order._program_check_compute_points(self.program)[self.program]

    def _set_domain_for_partner(self):
        self.program.sudo().sale_domain = repr([("partner_id", "=", self.partner.id)])

    def test_default_domain_is_empty_and_does_not_restrict(self):
        self.assertEqual(self.program.sale_domain, "[]")
        self.assertFalse(self.program._get_valid_sale_order())
        for partner in (self.partner, self.other_partner):
            result = self._check(self._create_order(partner))
            self.assertNotIn("error", result)
            self.assertIn("points", result)

    def test_get_valid_sale_order_returns_the_domain(self):
        self._set_domain_for_partner()
        self.assertEqual(
            Domain(self.program._get_valid_sale_order()),
            Domain([("partner_id", "=", self.partner.id)]),
        )
        self.program.sudo().sale_domain = False
        self.assertFalse(self.program._get_valid_sale_order())

    def test_order_inside_the_domain_is_valid(self):
        self._set_domain_for_partner()
        result = self._check(self._create_order())
        self.assertNotIn("error", result)
        self.assertIn("points", result)

    def test_order_outside_the_domain_gets_the_generic_error(self):
        self._set_domain_for_partner()
        result = self._check(self._create_order(self.other_partner))
        self.assertIn("error", result)
        self.assertNotIn("points", result)
        self.assertIn(self.program.name, result["error"])

    def test_order_outside_the_domain_gets_the_custom_message(self):
        self._set_domain_for_partner()
        self.program.sudo().not_applicable_message = "Only for the registered partner"
        result = self._check(self._create_order(self.other_partner))
        self.assertEqual(result["error"], "Only for the registered partner")

    def test_domain_does_not_replace_an_existing_error(self):
        self._set_domain_for_partner()
        order = self._create_order(self.other_partner)
        order.order_line.product_uom_qty = 0
        result = self._check(order)
        self.assertIn("error", result)
        self.assertNotIn(self.program.name, result["error"])

    def _claimable_programs(self, order):
        order._update_programs_and_rewards()
        return {coupon.program_id for coupon in order._get_claimable_rewards()}

    def test_rewards_are_claimable_only_inside_the_domain(self):
        self._set_domain_for_partner()
        self.assertIn(self.program, self._claimable_programs(self._create_order()))
        self.assertNotIn(self.program, self._claimable_programs(self._create_order(self.other_partner)))

    def test_rewards_are_claimable_for_everyone_without_a_domain(self):
        for partner in (self.partner, self.other_partner):
            self.assertIn(self.program, self._claimable_programs(self._create_order(partner)))
