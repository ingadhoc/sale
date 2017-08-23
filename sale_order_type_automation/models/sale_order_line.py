# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import api, models
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _prepare_invoice_line(self, qty):
        """
        Forzamos compania de diario de sale type
        """
        if self.order_id.type_id.journal_id:
            self = self.with_context(
                force_company=self.order_id.type_id.journal_id.company_id.id)
        return super(SaleOrderLine, self)._prepare_invoice_line(qty)
