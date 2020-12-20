##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ignore_exception_print = fields.Boolean(
        'Ignore Exceptions Print',
        copy=False,
    )

    def print_quotation(self):
        if self.detect_print_exceptions():
            return self.with_context(print_exceptions=True)._popup_exceptions()
        else:
            return super().print_quotation()

    def action_quotation_send(self):
        self.ensure_one()
        if self.detect_print_exceptions():
            return self.with_context(print_exceptions=True)._popup_exceptions()
        else:
            return super().action_quotation_send()

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

    # Improvement to be able to send things by context to the
    # pop up of exceptions
    def _popup_exceptions(self):
        action = super(SaleOrder, self)._popup_exceptions()
        ctx = self._context.copy()
        ctx.update({
            'active_id': self.ids[0],
            'active_ids': self.ids,
            'active_model': self._name,
        })
        action.update({
            'context': ctx
        })
        return action
