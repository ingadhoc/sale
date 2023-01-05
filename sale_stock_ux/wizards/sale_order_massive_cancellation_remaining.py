##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class ActionCancel(models.TransientModel):
    _name = "sale_stock_ux.action_mass_cancel_remaining.wizard"
    _description = "Wizard to do a massive cancellation of remaining quantities "

    def action_mass_cancel_remaining(self):
        order = self.env['sale.order'].browse(self._context.get('active_ids', []))
        records = order.mapped('order_line').filtered(lambda x: x.delivery_status == 'to deliver')
        for rec in records:
            rec.button_cancel_remaining()
