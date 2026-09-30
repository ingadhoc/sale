from odoo.addons.pos_ux.hooks import post_init_hook
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPaymentMethod(TransactionCase):
    """Tests for the "Identify Customer" default and for the install hook that
    applies it to the payment methods that already exist."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Test POS Cash",
                "type": "cash",
                "code": "TPOSC",
            }
        )
        cls.payment_method = cls.env["pos.payment.method"].create(
            {
                "name": "Test Payment Method",
                "journal_id": cls.journal.id,
            }
        )

    def _disable_identify_customer(self):
        self.env.cr.execute(
            "UPDATE pos_payment_method SET split_transactions = false WHERE id = %s",
            (self.payment_method.id,),
        )
        self.payment_method.invalidate_recordset(["split_transactions"])

    def test_new_payment_method_identifies_customer(self):
        self.assertTrue(self.payment_method.split_transactions)

    def test_post_init_hook_enables_identify_customer(self):
        self._disable_identify_customer()
        self.assertFalse(self.payment_method.split_transactions)
        post_init_hook(self.env)
        self.assertTrue(self.payment_method.split_transactions)

    def test_post_init_hook_reaches_methods_with_open_session(self):
        config = self.env["pos.config"].create(
            {
                "name": "Test POS",
                "payment_method_ids": [(6, 0, self.payment_method.ids)],
            }
        )
        self.env["pos.session"].create({"config_id": config.id, "user_id": self.env.user.id})
        self._disable_identify_customer()
        self.assertTrue(self.payment_method.open_session_ids)
        post_init_hook(self.env)
        self.assertTrue(self.payment_method.split_transactions)
