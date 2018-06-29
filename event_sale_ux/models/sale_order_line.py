##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import api, models, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def open_sale_line_form(self):
        self.ensure_one()
        view_id = self.env.ref('event_sale_ux.view_order_line_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Order Line'),
            'res_model': 'sale.order.line',
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'flags': {'form': {
                    'action_buttons': True,
                    'options': {'mode': 'edit'}}},
        }
