##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestLockedOrderLines(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # sale_exception may rollback the whole transaction inside action_confirm.
        if "exception.rule" in cls.env:
            cls.env["exception.rule"].sudo().search([]).write({"active": False})
        cls.product = cls._create_product(name="Locked order product", type="consu", invoice_policy="order")

    def _create_locked_order(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 1})],
            }
        )
        order.action_confirm()
        order.action_lock()
        self.assertTrue(order.locked)
        return order

    def test_cannot_add_line_to_locked_order(self):
        order = self._create_locked_order()
        with self.assertRaises(UserError):
            order.write({"order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 1})]})
        self.assertEqual(len(order.order_line), 1)

    def test_can_add_line_to_unlocked_order(self):
        order = self._create_locked_order()
        order.action_unlock()
        order.write({"order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 1})]})
        self.assertEqual(len(order.order_line), 2)

    def test_down_payment_on_locked_order(self):
        order = self._create_locked_order()
        self.env["sale.advance.payment.inv"].with_context(active_model="sale.order", active_ids=order.ids).create(
            {"advance_payment_method": "fixed", "fixed_amount": 10.0}
        ).create_invoices()
        self.assertTrue(order.order_line.filtered("is_downpayment"))
