##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_status = fields.Selection(selection_add=[
        ('no', 'Nothing to Deliver'),
    ],
        readonly=True,
        default='no'
    )
    force_delivery_status = fields.Selection([
        ('no', 'Nothing to Deliver'),
        ('full', 'Fully Delivered'),
    ],
        tracking=True,
        copy=False,
    )

    with_returns = fields.Boolean(
        compute='_compute_with_returns',
        store=True,
    )

    @api.depends('order_line.quantity_returned')
    def _compute_with_returns(self):
        for order in self:
            order.with_returns = any(line.quantity_returned
                                     for line in order.order_line)

    def action_cancel(self):
        for order in self.filtered(lambda order: order.picking_ids.filtered(
                lambda x: x.state == 'done')):
            raise UserError(_(
                'Unable to cancel sale order %s as some deliveries'
                ' have already been done.') % (order.name))
        return super().action_cancel()

    @api.depends('picking_ids', 'picking_ids.state', 'force_delivery_status')
    def _compute_delivery_status(self):
        super()._compute_delivery_status()
        for order in self:
            if not order.picking_ids or all(p.state == 'cancel' for p in order.picking_ids):
                order.delivery_status = 'no'
                continue
            if order.force_delivery_status:
                order.delivery_status = order.force_delivery_status
                continue

    def write(self, vals):
        self.check_force_delivery_status(vals)
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.check_force_delivery_status(vals)
        return super().create(vals_list)

    @api.model
    def check_force_delivery_status(self, vals):
        if vals.get('force_delivery_status') and not self.user_has_groups(
                'base.group_system'):
            group = self.env.ref('base.group_system').sudo()
            raise UserError(_(
                'Only users with "%s / %s" can Set Delivered manually') % (
                group.category_id.name, group.name))
