# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, fields
import openerp.addons.decimal_precision as dp


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    qty_returned = fields.Float(
        string='Returned',
        copy=False,
        default=0.0,
        digits=dp.get_precision('Product Unit of Measure'),
    )

    @api.multi
    @api.depends('qty_delivered', 'qty_returned')
    def _compute_all_qty_delivered(self):
        for rec in self:
            rec.all_qty_delivered = rec.qty_delivered + rec.qty_returned

    @api.multi
    def _get_delivered_qty(self):
        # every time delivered qty is updated, we update qty returned
        self._get_qty_returned()
        return super(SaleOrderLine, self)._get_delivered_qty()

    @api.multi
    def _get_qty_returned(self):
        for rec in self:
            qty_returned = 0.0
            # we use same method as in sale_stock_picking_return_invoicing
            for move in rec.procurement_ids.mapped('move_ids').filtered(
                lambda r: (r.state == 'done' and
                           not r.scrapped and
                           r.location_dest_id.usage != "customer" and
                           r.to_refund_so)):
                qty_returned += move.product_uom._compute_qty_obj(
                    move.product_uom, move.product_uom_qty, rec.product_uom)
            rec.qty_returned = qty_returned


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    with_returns = fields.Boolean(
        compute='_compute_with_returns',
        store=True,
    )

    @api.multi
    @api.depends('order_line.qty_returned')
    def _compute_with_returns(self):
        for order in self:
            if any(line.qty_returned for line in order.order_line):
                order.with_returns = True
            else:
                order.with_returns = False
