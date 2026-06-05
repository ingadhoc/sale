from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import SaleGatheringCommon


@tagged("post_install", "-at_install")
class TestSaleGatheringOrderLine(SaleGatheringCommon):
    def test_cannot_change_discount_on_confirmed_gathering_line(self):
        order = self._confirm_gathering_order()

        with self.assertRaises(UserError):
            order.order_line.write({"discount": 10.0})
