##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.addons.base_exception.tests.common import (
    patch_base_exception_method_env,
    swallow_base_exception_error,
)
from odoo.addons.sale_exception.tests.common import patch_detect_exception_method_env
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleExceptionPartnerState(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, test_base_exception=True, tracking_disable=True))
        cls.company = cls.env.company
        cls.pricelist = cls.env["product.pricelist"].create({"name": "Test Pricelist"})
        cls.product = cls.env["product.product"].create({"name": "Test Product", "type": "consu", "list_price": 100.0})
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})
        cls.rule_unapproved = cls.env.ref("sale_exception_partner_state.unapproved_partner_restriction")
        cls.rule_amount = cls.env.ref("sale_exception_partner_state.unapproved_partner_amount_restriction")

    def _create_order(self, partner, qty=1):
        return self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "pricelist_id": self.pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": qty,
                            "price_unit": self.product.list_price,
                        }
                    )
                ],
            }
        )

    @patch_base_exception_method_env
    @patch_detect_exception_method_env
    @swallow_base_exception_error
    def _confirm(self, order):
        order.action_confirm()

    def test_restrict_yes_blocks_unapproved_partner(self):
        self.company.restrict_sales = "yes"
        self.partner.partner_state = "potential"
        order = self._create_order(self.partner)
        self._confirm(order)
        self.assertEqual(order.state, "draft")
        self.assertIn(self.rule_unapproved, order.exception_ids)

    def test_restrict_yes_allows_approved_partner(self):
        self.company.restrict_sales = "yes"
        self.partner.partner_state = "approved"
        order = self._create_order(self.partner)
        self._confirm(order)
        self.assertEqual(order.state, "sale")
        self.assertNotIn(self.rule_unapproved, order.exception_ids)

    def test_restrict_amount_blocks_over_the_amount(self):
        self.company.restrict_sales = "amount_depends"
        self.company.restrict_sales_amount = 150.0
        self.partner.partner_state = "potential"
        order = self._create_order(self.partner, qty=2)
        self.assertGreaterEqual(order.amount_total, 150.0)
        self._confirm(order)
        self.assertEqual(order.state, "draft")
        self.assertIn(self.rule_amount, order.exception_ids)
        self.assertNotIn(self.rule_unapproved, order.exception_ids)

    def test_restrict_amount_allows_under_the_amount(self):
        self.company.restrict_sales = "amount_depends"
        self.company.restrict_sales_amount = 150.0
        self.partner.partner_state = "potential"
        order = self._create_order(self.partner)
        self.assertLess(order.amount_total, 150.0)
        self._confirm(order)
        self.assertEqual(order.state, "sale")
        self.assertFalse(order.exception_ids)

    def test_the_state_checked_is_the_commercial_partner_one(self):
        self.company.restrict_sales = "yes"
        self.partner.partner_state = "approved"
        contact = self.env["res.partner"].create(
            {"name": "Test Contact", "parent_id": self.partner.id, "type": "invoice"}
        )
        self.assertEqual(contact.commercial_partner_id, self.partner)
        self.assertNotEqual(contact.partner_state, "approved")
        order = self._create_order(contact)
        self._confirm(order)
        self.assertEqual(order.state, "sale")

    def test_settings_write_the_company_fields(self):
        settings = self.env["res.config.settings"].create(
            {"restrict_sales": "amount_depends", "restrict_sales_amount": 500.0}
        )
        settings.execute()
        self.assertEqual(self.company.restrict_sales, "amount_depends")
        self.assertEqual(self.company.restrict_sales_amount, 500.0)
