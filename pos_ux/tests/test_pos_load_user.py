from odoo import SUPERUSER_ID
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPosLoadUser(TransactionCase):
    def test_archived_current_user_is_loaded(self):
        """The POS loads the current user even when it is archived, as the
        superuser is."""
        users = self.env["res.users"].with_user(SUPERUSER_ID)
        self.assertFalse(users.browse(SUPERUSER_ID).active)
        data = users._load_pos_metadata({})
        self.assertEqual(data["res.users"]["records"].ids, [SUPERUSER_ID])
