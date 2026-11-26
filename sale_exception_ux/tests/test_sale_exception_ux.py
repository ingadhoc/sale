##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase


class TestSaleExceptionUx(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Only the rules of this test decide, no matter what the database carries
        cls.env["exception.rule"].search([]).write({"active": False})
        cls.partner = cls.env["res.partner"].create({"name": "Exception UX Partner"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Exception UX Product",
                "type": "consu",
                "list_price": 100.0,
            }
        )
        cls.rule = cls.env["exception.rule"].create(
            {
                "name": "Needs a reference",
                "model": "sale.order",
                "exception_type": "by_py_code",
                "code": "failed = self.client_order_ref == 'ignorable'",
                "sequence": 10,
            }
        )
        cls.line_rule = cls.env["exception.rule"].create(
            {
                "name": "Needs more than one unit",
                "model": "sale.order.line",
                "exception_type": "by_py_code",
                "code": "failed = self.product_uom_qty < 2",
                "sequence": 20,
                "active": False,
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

    def test_ignoring_confirms_the_quotation(self):
        """A rule that does not block is ignored and the order confirmed in one step."""
        order = self._new_order("ignorable")
        order.action_ignore_exceptions()
        self.assertTrue(order.ignore_exception)
        self.assertEqual(order.state, "sale")

    def test_a_blocking_rule_stops_an_already_ignored_quotation(self):
        """The rules are checked again, even when the order was ignored before.

        This is the case the module fixes: the order was ignored while only a
        rule that does not block failed, and the rule turned blocking afterwards.
        """
        order = self._new_order("ignorable")
        order.exception_ids = self.rule
        order.ignore_exception = True
        self.rule.is_blocking = True
        with self.assertRaises(UserError) as error:
            order.action_ignore_exceptions()
        self.assertIn(self.rule.name, str(error.exception))
        self.assertEqual(order.state, "draft")

    def test_a_blocking_exception_that_no_longer_fails_does_not_stop_the_button(self):
        """The stored exceptions are a snapshot, what fails right now decides."""
        order = self._new_order("no-rule")
        self.rule.is_blocking = True
        order.exception_ids = self.rule
        order.action_ignore_exceptions()
        self.assertEqual(order.state, "sale")
        self.assertFalse(order.exception_ids)

    def test_the_quotation_is_not_ignored_when_the_confirmation_fails(self):
        """Both steps live in the same transaction, so neither is left half done."""
        order = self._new_order("ignorable")
        with (
            self.assertRaises(UserError),
            self.env.cr.savepoint(),
            patch.object(type(order), "action_confirm", side_effect=UserError("No way")),
        ):
            order.action_ignore_exceptions()
        self.assertFalse(order.ignore_exception)
        self.assertEqual(order.state, "draft")

    def test_a_confirmed_order_is_only_ignored(self):
        """The alert also shows on a confirmed order, which cannot be confirmed again."""
        order = self._new_order("no-rule")
        order.action_confirm()
        order.client_order_ref = "ignorable"
        order.action_ignore_exceptions()
        self.assertTrue(order.ignore_exception)
        self.assertEqual(order.state, "sale")

    def test_the_wizard_confirms_only_once(self):
        """Ignoring from the popup goes through the order, which already confirms."""
        self.env.company.sale_exception_show_popup = True
        order = self._new_order("ignorable")
        order.exception_ids = self.rule
        action = order.action_popup_exceptions()
        wizard = self.env["sale.exception.confirm"].with_context(**action["context"]).create({"ignore": True})
        wizard.action_confirm()
        self.assertTrue(order.ignore_exception)
        self.assertEqual(order.state, "sale")

    def test_a_blocking_line_rule_stops_the_button(self):
        """The rules of the lines decide too, not only the ones of the order."""
        order = self._new_order("no-rule")
        self.line_rule.write({"active": True, "is_blocking": True})
        with self.assertRaises(UserError) as error:
            order.action_ignore_exceptions()
        self.assertIn(self.line_rule.name, str(error.exception))
        self.assertEqual(order.state, "draft")

    def test_a_line_rule_that_does_not_block_is_ignored(self):
        """A line in exception is ignored and the order confirmed in one step."""
        self.line_rule.active = True
        order = self._new_order("no-rule")
        order.action_ignore_exceptions()
        self.assertTrue(order.ignore_exception)
        self.assertEqual(order.state, "sale")
