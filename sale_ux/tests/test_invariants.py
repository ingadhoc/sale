##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import tagged

from .common import SaleUxCommon


@tagged("post_install", "-at_install")
class TestSaleUxInvariants(SaleUxCommon):
    """The battery is verified in both directions: it must not bother a sane
    operation, and it must catch the defective one it exists to catch."""

    def test_invariant_accepts_a_sane_cron_run(self):
        """assert_cron_cancelled_exactly stays quiet when the cron cancels
        exactly the expired quotations and leaves the recent one alone."""
        # Enable the cancellation with a 10 day window
        self.IrConfig.set_param("sale_ux.cancel_old_quotations", "True")
        self.IrConfig.set_param("sale_ux.days_to_keep_quotations", "10")
        expired = self._create_old_quotation(days_old=20)
        recent = self._create_old_quotation(days_old=2)
        universe = expired | recent
        # Capture the states before the operation under test
        previous_states = self.snapshot_states(universe)

        self.env["sale.order"]._cron_clean_old_quotations()

        self.assert_cron_cancelled_exactly(universe, expired, previous_states)

    def test_invariant_catches_an_extra_cancellation(self):
        """A quotation cancelled beyond what the scenario declared is the
        collateral damage the battery exists to surface."""
        expected = self._create_old_quotation(days_old=20)
        bystander = self._create_old_quotation(days_old=2)
        universe = expected | bystander
        previous_states = self.snapshot_states(universe)
        # The operation overreaches and cancels the bystander too
        universe._action_cancel()

        with self.assertRaises(AssertionError) as error:
            self.assert_cron_cancelled_exactly(universe, expected, previous_states)

        self.assertIn(bystander.name, str(error.exception))

    def test_invariant_catches_a_missing_cancellation(self):
        """A quotation the scenario expected cancelled and survived has to fail
        the battery, not pass silently."""
        expected = self._create_old_quotation(days_old=20)
        also_expected = self._create_old_quotation(days_old=30)
        universe = expected | also_expected
        previous_states = self.snapshot_states(universe)
        # Only one of the two expired quotations gets cancelled
        expected._action_cancel()

        with self.assertRaises(AssertionError) as error:
            self.assert_cron_cancelled_exactly(universe, universe, previous_states)

        self.assertIn(also_expected.name, str(error.exception))

    def test_invariant_catches_a_collateral_state_change(self):
        """The number can be right and the record next to it still be broken:
        an untouched quotation that changed state must fail the battery."""
        expected = self._create_old_quotation(days_old=20)
        bystander = self._create_old_quotation(days_old=2)
        universe = expected | bystander
        previous_states = self.snapshot_states(universe)
        # The cancellation is correct, but the bystander moved anyway
        expected._action_cancel()
        bystander.state = "sent"

        with self.assertRaises(AssertionError) as error:
            self.assert_cron_cancelled_exactly(universe, expected, previous_states)

        self.assertIn("Collateral damage", str(error.exception))
        self.assertIn(bystander.name, str(error.exception))
