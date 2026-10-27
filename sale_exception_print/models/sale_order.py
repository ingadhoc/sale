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
        self.detect_print_exceptions()
        return super().action_quotation_send()

    def action_preview_sale_order(self):
        self.ensure_one()
        self.detect_print_exceptions()
        return super().action_preview_sale_order()

    @api.model
    def action_share(self):
        self.ensure_one()
        self.detect_print_exceptions()
        return super().action_share()

    def detect_print_exceptions(self):
        """Detect the exceptions that block printing the considered sale orders.

        Since 20.0 base_exception stores the exceptions in a separate
        transaction and raises BaseExceptionError instead of returning them,
        so the popup is shown by the error handler of this module.
        """
        orders = (
            self.with_context(print_exceptions=True)
            .exists()
            .filtered(lambda order: not order.ignore_exception and not order.ignore_exception_print)
        )
        if not orders:
            return []
        return orders.detect_exceptions()

    def _must_popup_exception(self):
        """The print flow always pops up, no matter the company setting."""
        if self.env.context.get("print_exceptions", False):
            return True
        return super()._must_popup_exception()

    # Improvement to be able to send things by context to the
    # pop up of exceptions
    def _popup_exceptions(self):
        action = super()._popup_exceptions()
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
