##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def run_invoicing_atomation(self):
        gathering_lines = self.filtered('is_gathering')
        super(SaleOrder, gathering_lines.with_context(invoice_gathering=True)).run_invoicing_atomation()
        super(SaleOrder, self - gathering_lines).run_invoicing_atomation()
