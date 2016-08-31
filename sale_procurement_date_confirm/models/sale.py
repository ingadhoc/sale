# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    date_confirm = fields.Date(
        'Confirmation Date',
        readonly=True,
        select=True,
        help="Date on which sales order is confirmed.", copy=False)

    @api.multi
    def action_confirm(self):
        self.write({'date_confirm': fields.Date.today()})
        return super(SaleOrder, self).action_confirm()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _prepare_order_line_procurement(self, group_id=False):
        res = super(SaleOrderLine, self)._prepare_order_line_procurement(
            group_id=group_id)
        if self.order_id.date_confirm:
            res['date_planned'] = datetime.strptime(self.order_id.date_confirm, "%Y-%m-%d")\
                + timedelta(days=self.customer_lead or 0.0) - \
                timedelta(days=self.order_id.company_id.security_lead)
        return res
