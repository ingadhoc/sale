##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _recheck_exceptions(self):
        """Evaluate every rule right now and store what fails on the orders.

        ``exception_ids`` holds the result of the last detection, and an order
        with ``ignore_exception`` is left out of every detection that follows,
        so neither of them tells whether a blocking rule fails today.
        """
        orders = self.with_context(recheck_ignored_exceptions=True)
        for records in (orders, orders.order_line):
            __, rules_to_remove, rules_to_add = records._get_exceptions()
            for rule_id, rule_orders in rules_to_remove.items():
                rule_orders.exception_ids = [Command.unlink(rule_id)]
            for rule_id, rule_orders in rules_to_add.items():
                rule_orders.exception_ids = [Command.link(rule_id)]
        return self.exception_ids

    def action_ignore_exceptions(self):
        """Ignore the exceptions and confirm the orders in a single step.

        Setting the flag on its own used to leave the order out of every later
        detection, so a rule that turned blocking afterwards, or an order that
        stopped meeting one, confirmed without any warning. Both happen in the
        same transaction, so an order whose confirmation fails is not ignored.
        """
        blocking = self._recheck_exceptions().filtered("is_blocking")
        if blocking:
            raise UserError(
                self.env._(
                    "These exceptions are blocking and can not be ignored:\n%(exceptions)s",
                    exceptions="\n".join(blocking.mapped("name")),
                )
            )
        res = super().action_ignore_exceptions()
        # A confirmed order shows the alert too, and confirming it again fails.
        self.filtered(lambda order: order.state in ("draft", "sent")).action_confirm()
        return res
