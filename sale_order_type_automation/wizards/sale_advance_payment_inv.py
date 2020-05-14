##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _create_invoice(self, order, so_line, amount):
        if order.type_id.journal_id:
            self = self.with_context(
                default_sale_type_id=order.type_id.id,
                default_journal_id=order.type_id.journal_id.id,
            )
        return super()._create_invoice(
            order=order, so_line=so_line, amount=amount)
