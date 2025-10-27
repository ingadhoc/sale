##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ignore_exception_print = fields.Boolean(
        "Ignore Exceptions Print",
        copy=False,
    )

    def action_quotation_send(self):
        self.ensure_one()
        if self.detect_print_exceptions():
            return self.with_context(print_exceptions=True)._popup_exceptions()
        else:
            return super().action_quotation_send()

    def action_preview_sale_order(self):
        self.ensure_one()
        if self.detect_print_exceptions():
            return self.with_context(print_exceptions=True)._popup_exceptions()
        else:
            return super().action_preview_sale_order()

    @api.model
    def action_share(self):
        self.ensure_one()
        if self.detect_print_exceptions():
            return self.with_context(print_exceptions=True)._popup_exceptions()
        else:
            return super().action_share()

    def detect_print_exceptions(self):
        """returns the list of exception_ids for all the considered sale orders

        as a side effect, the sale order's exception_ids column is updated with
        the list of exceptions related to the SO
        """

        all_exception_ids = []
        for order in self.with_context(print_exceptions=True):
            if order.ignore_exception or order.ignore_exception_print:
                continue
            exception_ids = order.detect_exceptions()
            order.exception_ids = [(6, 0, exception_ids)]
            all_exception_ids += exception_ids
        return all_exception_ids

    @api.model
    def check_print_exceptions_for_action(self, order_ids):
        """Check if any of the orders have print exceptions.
        Called from JavaScript before printing.
        Returns a dict with 'has_exceptions' and 'action' if exceptions found.
        """
        orders = self.env["sale.order"].browse(order_ids)
        for order in orders:
            exception_ids = order.detect_print_exceptions()
            if exception_ids:
                return {"has_exceptions": True, "action": order.with_context(print_exceptions=True)._popup_exceptions()}
        return {"has_exceptions": False}

    # Improvement to be able to send things by context to the
    # pop up of exceptions
    def _popup_exceptions(self):
        action = super(SaleOrder, self)._popup_exceptions()
        ctx = self.env.context.copy()
        ctx.update(
            {
                "active_id": self.ids[0],
                "active_ids": self.ids,
                "active_model": self._name,
            }
        )
        action.update({"context": ctx})
        return action
