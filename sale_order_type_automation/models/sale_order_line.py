##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # @api.multi
    # def _prepare_invoice_line(self, qty):
    #     """
    #     Forzamos compania de diario de sale type
    #     """
    #     if self.order_id.type_id.journal_id:
    #         self = self.with_context(
    #             force_company=self.order_id.type_id.journal_id.company_id.id)
    #     return super(SaleOrderLine, self)._prepare_invoice_line(qty)

    @api.multi
    def invoice_line_create(self, invoice_id, qty):
        """
        Forzamos compania de diario de sale type
        IMPORTANTE: lo hacemos en este metodo y no en _prepare_invoice_line
        ya que ese se itera para cada linea y el with_context hace que se
        pierda cache y mata la performance
        """
        if self.order_id.type_id.journal_id:
            self = self.with_context(
                force_company=self.order_id.type_id.journal_id.company_id.id)
        return super(SaleOrderLine, self).invoice_line_create(invoice_id, qty)
