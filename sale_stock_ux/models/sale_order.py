##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_status = fields.Selection([
        ('no', 'Nothing to Deliver'),
        ('to deliver', 'To Deliver'),
        ('delivered', 'Delivered'),
    ],
        compute='_compute_delivery_status',
        store=True,
        readonly=True,
        default='no'
    )
    force_delivery_status = fields.Selection([
        ('no', 'Nothing to Deliver'),
        ('delivered', 'Delivered'),
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
                'Unable to cancel sale order %s as some receptions'
                ' have already been done.') % (order.name))
        return super().action_cancel()

    # dejamos el depends a qty_delivered por mas que usamos all_qty_delivered
    # total son iguales pero qty_delivered es storeado
    @api.depends(
        'state', 'order_line.qty_delivered', 'order_line.product_uom_qty',
        'force_delivery_status')
    def _compute_delivery_status(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for order in self:
            if order.state not in ('sale', 'done'):
                order.delivery_status = 'no'
                continue

            if order.force_delivery_status:
                order.delivery_status = order.force_delivery_status
                continue

            if any(float_compare(
                    line.all_qty_delivered, line.product_uom_qty,
                    precision_digits=precision) == -1
                    for line in order.order_line):
                delivery_status = 'to deliver'
            elif all(float_compare(
                    line.all_qty_delivered, line.product_uom_qty,
                    precision_digits=precision) >= 0
                    for line in order.order_line):
                delivery_status = 'delivered'
            else:
                delivery_status = 'no'
            order.delivery_status = delivery_status

    def write(self, vals):
        self.check_force_delivery_status(vals)
        return super().write(vals)

    @api.model
    def create(self, vals):
        self.check_force_delivery_status(vals)
        return super().create(vals)

    @api.model
    def check_force_delivery_status(self, vals):
        if vals.get('force_delivery_status') and not self.user_has_groups(
                'base.group_system'):
            group = self.env.ref('base.group_system').sudo()
            raise UserError(_(
                'Only users with "%s / %s" can Set Delivered manually') % (
                group.category_id.name, group.name))
