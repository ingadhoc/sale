##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.base_exception.exceptions import BaseExceptionError
from odoo.tests import TransactionCase


class TestSaleExceptionPrint(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Only the rules of this test decide, no matter what the database carries
        cls.env["exception.rule"].search([]).write({"active": False})
        cls.partner = cls.env["res.partner"].create({"name": "Print Exception Partner"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Print Exception Product",
                "type": "consu",
                "list_price": 100.0,
            }
        )
        cls.print_rule = cls.env["exception.rule"].create(
            {
                "name": "Blocks printing",
                "model": "sale.order",
                "exception_type": "by_py_code",
                "code": "failed = self.client_order_ref == 'block-print'",
                "block_print": True,
                "sequence": 10,
            }
        )
        cls.confirm_rule = cls.env["exception.rule"].create(
            {
                "name": "Blocks confirmation only",
                "model": "sale.order",
                "exception_type": "by_py_code",
                "code": "failed = self.client_order_ref == 'block-confirm'",
                "sequence": 20,
            }
        )

    def _new_order(self, client_order_ref):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "client_order_ref": client_order_ref,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 1})],
            }
        )

    def test_print_exception_detection(self):
        """Which exceptions stop printing a quotation, and which ones do not.

        base_exception stores the exceptions in its own transaction, so the
        tests check what the module decides: whether the action is stopped.
        """
        with self.subTest("a rule that blocks printing stops the action"):
            order = self._new_order("block-print")
            with self.assertRaises(BaseExceptionError):
                order.detect_print_exceptions()

        with self.subTest("a rule that does not block printing lets it through"):
            order = self._new_order("block-confirm")
            self.assertFalse(order.detect_print_exceptions())

        with self.subTest("a confirmation exception does not stop printing"):
            order = self._new_order("no-rule")
            order.exception_ids = self.confirm_rule
            self.assertFalse(order.detect_print_exceptions())

        with self.subTest("an order with the print exceptions ignored is not stopped"):
            order = self._new_order("block-print")
            order.ignore_exception_print = True
            self.assertFalse(order.detect_print_exceptions())

        with self.subTest("an order with every exception ignored is not stopped"):
            order = self._new_order("block-print")
            order.ignore_exception = True
            self.assertFalse(order.detect_print_exceptions())

    def test_wizard_ignores_the_print_exceptions_only(self):
        """Ignoring from the print popup does not ignore nor confirm the order."""
        order = self._new_order("block-print")
        order.exception_ids = self.print_rule
        action = order.with_context(print_exceptions=True).action_popup_exceptions()
        wizard = self.env["sale.exception.confirm"].with_context(**action["context"]).create({"ignore": True})
        self.assertEqual(wizard.related_model_id, order)
        wizard.action_confirm()
        self.assertTrue(order.ignore_exception_print)
        self.assertFalse(order.ignore_exception)
        self.assertEqual(order.state, "draft")

    def test_print_popup_does_not_depend_on_the_company_setting(self):
        """The print flow always pops up, the confirmation one obeys the setting."""
        self.env.company.sale_exception_show_popup = False
        order = self._new_order("block-print")
        self.assertTrue(order.with_context(print_exceptions=True)._must_popup_exception())
        self.assertFalse(order._must_popup_exception())
