from odoo import fields, models, api


class TaskStopRunningTimersConfirmation(models.TransientModel):
    _name = 'sale.order.cancel.remaining'
    _description = 'Sale Order Cancel Remaining'

    sale_order_line_ids = fields.Many2many('sale.order.line',
                                        required=True,
                                        default=lambda self: self.default_sale_order_line_ids())

    @api.model
    def default_sale_order_line_ids(self):
        return self.env['sale.order'].browse(
            self._context.get('active_ids', [])).mapped('order_line')

    def action_confirm(self):
        self.sale_order_line_ids.filtered(lambda x: x.delivery_status == 'to deliver').with_context(cancel_from_order=True).button_cancel_remaining()
