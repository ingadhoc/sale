from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductArchive(TransactionCase):
    """Tests for the guard that blocks archiving a variant sold in POS
    while a session is open, closing the gap left by
    `_unlink_or_archive`'s direct `write({'active': False})` fallback."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create({"name": "Test Chair", "available_in_pos": True})
        cls.config = cls.env["pos.config"].create({"name": "Test POS"})

    def _open_session(self):
        return self.env["pos.session"].create({"config_id": self.config.id, "user_id": self.env.user.id})

    def test_blocked_while_session_open(self):
        self._open_session()
        with self.assertRaises(UserError):
            self.product.write({"active": False})

    def test_allowed_when_no_open_session(self):
        self.product.write({"active": False})
        self.assertFalse(self.product.active)

    def test_allowed_when_not_available_in_pos(self):
        self._open_session()
        self.product.available_in_pos = False
        self.product.write({"active": False})
        self.assertFalse(self.product.active)
