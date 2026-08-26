##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################


class SaleUxInvariants:
    """Battery of invariants that must hold after a Sale UX operation.

    Test cases mix this class in through their ``common``, so every suite
    verifies the same properties over the records the test created itself.
    The battery has no switches: a scenario that legitimately breaks an
    invariant declares the exception in the test, not here.
    """

    def snapshot_states(self, orders):
        """Capture the state of every order before the operation under test."""
        return {order.id: order.state for order in orders}

    def assert_cron_cancelled_exactly(self, universe, expected_cancelled, previous_states):
        """Exactly ``expected_cancelled`` ended up cancelled, and nothing else moved.

        The check runs over ``universe`` only -- the records the test created --
        so unrelated orders living in the database never relax it.

        :param universe: every sale.order the test created
        :param expected_cancelled: the subset the scenario expects in ``cancel``
        :param previous_states: ``{id: state}`` taken before the operation
        """
        # The scenario must be internally consistent before anything is asserted
        self.assertFalse(
            expected_cancelled - universe,
            "The scenario expects orders outside the universe it declared: %s"
            % (expected_cancelled - universe).mapped("name"),
        )
        self.assertFalse(
            set(universe.ids) - set(previous_states),
            "No state was captured before the operation for: %s"
            % universe.filtered(lambda order: order.id not in previous_states).mapped("name"),
        )
        # Read the states again in case the operation ran through another environment
        universe.invalidate_recordset(["state"])
        cancelled = universe.filtered(lambda order: order.state == "cancel")
        self.assertFalse(
            cancelled - expected_cancelled,
            "Cancelled orders the scenario did not expect: %s" % (cancelled - expected_cancelled).mapped("name"),
        )
        self.assertFalse(
            expected_cancelled - cancelled,
            "Orders the scenario expected cancelled and are not: %s" % (expected_cancelled - cancelled).mapped("name"),
        )
        # Everything the scenario left out has to keep the state it already had
        for order in universe - expected_cancelled:
            self.assertEqual(
                order.state,
                previous_states[order.id],
                "Collateral damage: %s moved from '%s' to '%s' and the scenario did not ask for it"
                % (order.name, previous_states[order.id], order.state),
            )
