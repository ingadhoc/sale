# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, fields, _
from openerp.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    manually_set_invoiced = fields.Boolean(
        string='Manually Set Invoiced?',
        help='If you set this field to True, then all lines invoiceable lines'
        'will be set to invoiced?',
    )

    @api.multi
    def action_cancel(self):
        for order in self:
            for inv in order.invoice_ids:
                if inv and inv.state not in ('cancel', 'draft'):
                    raise UserError(_(
                        "Unable to cancel this sale order. You must first "
                        "cancel related bills and pickings."))
        return super(SaleOrder, self).action_cancel()

    @api.multi
    def button_reopen(self):
        self.write({'state': 'sale'})

    @api.multi
    @api.constrains('manually_set_invoiced')
    def check_manually_set_invoiced(self):
        if not self.user_has_groups('base.group_system'):
            group = self.env.ref('base.group_system').sudo()
            raise UserError(_(
                'Only users with "%s / %s" can Set Invoiced manually') % (
                group.category_id.name, group.name))

    # @api.multi
    # def button_set_invoiced(self):
    #     if not self.user_has_groups('base.group_system'):
    #         group = self.env.ref('base.group_system').sudo()
    #         raise UserError(_(
    #             'Only users with "%s / %s" can Set Invoiced manually') % (
    #             group.category_id.name, group.name))
    #     self.order_line.write({'qty_to_invoice': 0.0})
    #     self.message_post(body='Manually setted as invoiced')
