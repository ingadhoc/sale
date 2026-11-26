from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestSaleExceptionCompat(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.rule = cls.env.ref("sale_exception.excep_no_zip")
        cls.rule.active = True
        partner = cls.env["res.partner"].create({"name": "No ZIP customer"})
        product = cls.env["product.product"].create({"name": "Exception product"})
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [Command.create({"product_id": product.id, "product_uom_qty": 1})],
            }
        )

    def test_confirm_button_keeps_popup_flow(self):
        self.order.with_context(sale_exception_from_button=True).action_confirm()
        self.assertEqual(self.order.state, "draft")
        self.assertIn(self.rule, self.order.exception_ids)

    def test_other_callers_stop_on_blocked_confirmation(self):
        with self.assertRaisesRegex(ValidationError, self.rule.name):
            self.order.with_context(sale_exception_from_button=False).action_confirm()
        self.assertEqual(self.order.state, "draft")
