##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self):
        """
        Forzamos compania de diario de sale type
        """
        if self.order_id.type_id.journal_id:
            self = self.with_context(force_company=self.order_id.type_id.journal_id.company_id.id)
        return super(SaleOrderLine, self)._prepare_invoice_line()
