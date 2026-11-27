from unittest.mock import patch

from odoo.addons.bus.models.bus import BusBus
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAssetsVersion(TransactionCase):
    """Tests for the stamp that tells an open register its files are outdated."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.param = cls.env["ir.config_parameter"].sudo()
        cls.config = cls.env["pos.config"].create({"name": "Test POS assets"})
        cls.session = cls.env["pos.session"].create(
            {
                "config_id": cls.config.id,
                "user_id": cls.env.user.id,
            }
        )

    def _notified_channels(self):
        """Run the cron with the bus mocked and return what it sent."""
        with patch.object(BusBus, "_sendone", autospec=True) as sendone:
            self.env["pos.config"].notify_outdated_pos_sessions()
        return [call.args[1] for call in sendone.call_args_list]

    def test_version_is_stable(self):
        version = self.env["pos.config"].get_pos_assets_version()
        self.assertTrue(version)
        self.assertEqual(version, self.env["pos.config"].get_pos_assets_version())

    def test_first_run_only_stores_the_version(self):
        self.param.set_param("pos_ux.notified_assets_version", False)
        self.assertEqual(self._notified_channels(), [])
        self.assertEqual(
            self.param.get_param("pos_ux.notified_assets_version"),
            self.env["pos.config"].get_pos_assets_version(),
        )

    def test_nothing_is_notified_when_the_version_did_not_change(self):
        self.param.set_param("pos_ux.notified_assets_version", self.env["pos.config"].get_pos_assets_version())
        self.assertEqual(self._notified_channels(), [])

    def test_open_register_is_notified_when_the_version_changes(self):
        token = self.config._ensure_access_token()
        self.param.set_param("pos_ux.notified_assets_version", "an old version")
        self.assertIn(token, self._notified_channels())
        self.assertEqual(
            self.param.get_param("pos_ux.notified_assets_version"),
            self.env["pos.config"].get_pos_assets_version(),
        )

    def test_closed_register_is_not_notified(self):
        token = self.config._ensure_access_token()
        self.session.write({"state": "closed"})
        self.param.set_param("pos_ux.notified_assets_version", "an old version")
        self.assertNotIn(token, self._notified_channels())
