##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleAdvancePaymentInvWizard(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _create_invoices(self, sale_orders):
        # In batch, queue the per-invoice notifications instead of sending them by SMTP inside the request
        if len(sale_orders) > 1:
            sale_orders = sale_orders.with_context(mail_notify_force_send=False)
        return super()._create_invoices(sale_orders)
