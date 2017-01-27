# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class SaleGlobalDiscountWizard(models.TransientModel):
    _name = "sale.order.global_discount.wizard"

    type = fields.Selection(
        [('distributed_percentage', 'Distributed Percentage'),
         ('distributed_amount', 'Distributed Amount'),
         ('global_percentage', 'Global Percentage'),
         ('global_amount', 'Global Amount')],
        'Type', default='distributed_percentage')
    distributed_percentage = fields.Float('Distributed Discount %')
    distributed_amount = fields.Float('Distributed Amount')
    global_percentage = fields.Float('Discount %')
    global_amount = fields.Float('Discount Amount')
    discount_product_id = fields.Many2one(
        'product.product', ondelete='cascade')
    reason = fields.Char('Reason')

    @api.multi
    def confirm(self):
        self.ensure_one()
        order = self.env['sale.order'].browse(
            self._context.get('active_id', False))
        order_line_obj = self.env['sale.order.line']
        if self.type == 'distributed_percentage':
            for line in order.order_line:
                line.discount = self.distributed_percentage
            return True
        elif self.type == 'distributed_amount':
            dist_percentage = 100 * \
                              self.distributed_amount / order.amount_untaxed
            for line in order.order_line:
                line.discount = dist_percentage
            return True
        elif self.type in ['global_percentage', 'global_amount']:
            global_amount = self.global_amount \
                if self.type == 'global_amount' \
                else self.global_percentage * order.amount_untaxed / 100
            reason = self.reason if self.type == 'global_amount' \
                else '{}% {}'.format(self.global_percentage, self.reason)
            vals = {
                'order_id': order.id,
                'product_id': self.discount_product_id.id,
                'name': reason,
                'product_uom_qty': -1,
                'price_unit': global_amount}
            line_id = order_line_obj.create(vals)
            _logger.info('line id: {}'.format(line_id))
            return True
