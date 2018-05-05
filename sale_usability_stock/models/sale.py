# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from openerp import models, api, fields, _
from openerp.exceptions import UserError
from openerp.tools.float_utils import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_status = fields.Selection([
        ('no', 'Nothing to Deliver'),
        ('to deliver', 'To Deliver'),
        ('delivered', 'Delivered'),
    ],
        string='Delivery Status',
        compute='_get_delivered',
        store=True,
        readonly=True,
        default='no'
    )
    manually_set_delivered = fields.Boolean(
        string='Manually Set Delivered?',
        help='If you set this field to True, then all lines deliverable lines'
        'will be set to delivered?',
        track_visibility='onchange',
        copy=False,
    )

    picking_ids = fields.Many2many(
        'stock.picking',
        search='_search_picking_ids'
    )

    @api.model
    def _search_picking_ids(self, operator, operand):
        pickings = self.env['stock.picking'].search([
            ('group_id', '!=', False),
            '|', ('name', operator, operand),
            ('voucher_ids.name', operator, operand)])
        return [('name', 'in', pickings.mapped('origin'))]

    @api.multi
    def action_cancel(self):
        for order in self:
            for pick in order.picking_ids:
                if pick.state == 'done':
                    raise UserError(_(
                        'Unable to cancel sale order %s as some receptions'
                        ' have already been done.') % (order.name))
        return super(SaleOrder, self).action_cancel()

    # dejamos el depends a qty_delivered por mas que usamos all_qty_delivered
    # total son iguales pero qty_delivered es storeado
    @api.depends(
        'state', 'order_line.qty_delivered', 'order_line.product_uom_qty',
        'manually_set_delivered')
    def _get_delivered(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for order in self:
            if order.state not in ('sale', 'done'):
                order.delivery_status = 'no'
                continue

            if order.manually_set_delivered:
                order.delivery_status = 'delivered'
                continue

            if any(float_compare(
                    line.all_qty_delivered, line.product_uom_qty,
                    precision_digits=precision) == -1
                    for line in order.order_line):
                order.delivery_status = 'to deliver'
            elif all(float_compare(
                    line.all_qty_delivered, line.product_uom_qty,
                    precision_digits=precision) >= 0
                    for line in order.order_line):
                order.delivery_status = 'delivered'
            else:
                order.delivery_status = 'no'

    @api.multi
    def write(self, vals):
        self.check_manually_set_delivered(vals)
        return super(SaleOrder, self).write(vals)

    @api.model
    def create(self, vals):
        self.check_manually_set_delivered(vals)
        return super(SaleOrder, self).create(vals)

    @api.model
    def check_manually_set_delivered(self, vals):
        if vals.get('manually_set_delivered') and not self.user_has_groups(
                'base.group_system'):
            group = self.env.ref('base.group_system').sudo()
            raise UserError(_(
                'Only users with "%s / %s" can Set Delivered manually') % (
                group.category_id.name, group.name))
