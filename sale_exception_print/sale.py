##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ignore_exception_print = fields.Boolean(
        'Ignore Exceptions Print',
        copy=False
    )

    @api.multi
    def print_quotation(self):
        if self.detect_print_exceptions():
            return self.with_context(print_exceptions=True)._popup_exceptions()
        else:
            return super(SaleOrder, self).print_quotation()

    @api.multi
    def action_quotation_send(self):
        self.ensure_one()
        if self.detect_print_exceptions():
            return self.with_context(print_exceptions=True)._popup_exceptions()
        else:
            return super(SaleOrder, self).action_quotation_send()

    @api.multi
    def detect_print_exceptions(self):
        """returns the list of exception_ids for all the considered sale orders

        as a side effect, the sale order's exception_ids column is updated with
        the list of exceptions related to the SO
        """
        exception_obj = self.env['sale.exception']
        order_exceptions = exception_obj.search(
            [('model', '=', 'sale.order'), ('block_print', '=', True)])
        line_exceptions = exception_obj.search(
            [('model', '=', 'sale.order.line'), ('block_print', '=', True)])

        all_exception_ids = []
        for order in self:
            if order.ignore_exception or order.ignore_exception_print:
                continue
            exception_ids = order._detect_exceptions(order_exceptions,
                                                     line_exceptions)
            order.exception_ids = [(6, 0, exception_ids)]
            all_exception_ids += exception_ids
        return all_exception_ids

    # Improvement to be able to send things by context to the
    # pop up of exceptions
    @api.multi
    def _popup_exceptions(self):
        action = self.env.ref('sale_exception.action_sale_exception_confirm')
        action = action.read()[0]
        ctx = self._context.copy()
        ctx.update({
            'active_id': self.ids[0],
            'active_ids': self.ids
        })
        action.update({
            'context': ctx
        })
        return action


class SaleException(models.Model):
    _inherit = "sale.exception"

    block_print = fields.Boolean('Block Print')
