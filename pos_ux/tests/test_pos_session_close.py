from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPosSessionClose(TransactionCase):
    """Tests for the closing block: closing is refused if there are paid orders
    without invoice, only when the billing behavior is "Always Invoice"."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env["pos.config"].create({"name": "Test POS"})
        cls.session = cls.env["pos.session"].create(
            {
                "config_id": cls.config.id,
                "user_id": cls.env.user.id,
            }
        )

    def _make_paid_order(self):
        return self.env["pos.order"].create(
            {
                "session_id": self.session.id,
                "company_id": self.session.company_id.id,
                "state": "paid",
                "amount_tax": 0,
                "amount_total": 10,
                "amount_paid": 10,
                "amount_return": 0,
            }
        )

    def test_blocked_when_paid_order_without_invoice(self):
        self.config.billing_behavior = "invoice_required"
        order = self._make_paid_order()
        self.assertFalse(order.account_move)
        result = self.session._pos_ux_cannot_close_session()
        self.assertIsNotNone(result)
        self.assertEqual(result.get("type"), "pos_ux_unbilled")

    def test_blocked_even_in_contingency(self):
        self.config.billing_behavior = "invoice_required"
        self._make_paid_order()
        self.session.invoice_contingency = True
        result = self.session._pos_ux_cannot_close_session()
        self.assertIsNotNone(result)
        self.assertEqual(result.get("type"), "pos_ux_unbilled")

    def test_allowed_when_not_invoice_required(self):
        self._make_paid_order()
        for behavior in ("on_demand", "invoice_by_default"):
            self.config.billing_behavior = behavior
            result = self.session._pos_ux_cannot_close_session()
            self.assertFalse(result)

    def test_allowed_when_all_invoiced(self):
        self.config.billing_behavior = "invoice_required"
        order = self._make_paid_order()
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        dummy_move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
            }
        )
        order.account_move = dummy_move
        result = self.session._pos_ux_cannot_close_session()
        self.assertFalse(result)

    def test_close_session_from_ui_returns_the_block(self):
        self.config.billing_behavior = "invoice_required"
        self._make_paid_order()
        result = self.session.close_session_from_ui()
        self.assertFalse(result.get("status"))
        self.assertEqual(result.get("type"), "pos_ux_unbilled")
