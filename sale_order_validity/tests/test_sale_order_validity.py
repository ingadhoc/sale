##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from datetime import timedelta

from odoo import fields
from odoo.addons.sale.tests.common import SaleCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestSaleOrderValidity(SaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.quotation_validity_days = 30

    def test_validity_days_default_from_company(self):
        order = self._create_so()

        self.assertEqual(order.validity_days, 30)

    def test_validity_date_computed_from_days(self):
        order = self._create_so()

        order.validity_days = 10

        self.assertEqual(order.validity_date, order.date_order.date() + timedelta(days=10))

    def test_validity_date_falls_back_to_core_without_days(self):
        order = self._create_so()

        order.validity_days = 0

        self.assertEqual(order.validity_date, fields.Date.context_today(order) + timedelta(days=30))

    def test_validity_days_over_company_limit_is_rejected(self):
        order = self._create_so()

        with self.assertRaises(UserError):
            order.validity_days = 31
            order.flush_recordset()

    def test_expired_quotation_can_not_be_confirmed(self):
        order = self._create_so()
        order.validity_date = fields.Date.context_today(order) - timedelta(days=1)

        self.assertTrue(order.is_expired)
        with self.assertRaises(UserError):
            order.action_confirm()

    def test_update_date_prices_and_validity_refreshes_date_and_prices(self):
        order = self._create_so()
        order.date_order = fields.Datetime.now() - timedelta(days=5)
        order.order_line.price_unit = 1.0

        order.update_date_prices_and_validity()

        self.assertEqual(order.date_order.date(), fields.Date.context_today(order))
        self.assertEqual(order.validity_date, order.date_order.date() + timedelta(days=order.validity_days))
        self.assertEqual(order.order_line.price_unit, order.order_line.product_id.list_price)

    def test_date_order_is_copied(self):
        order = self._create_so()
        order.date_order = fields.Datetime.now() - timedelta(days=5)

        copied = order.copy()

        self.assertEqual(copied.date_order, order.date_order)
