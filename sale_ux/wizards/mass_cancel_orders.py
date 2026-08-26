##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleMassCancelOrders(models.TransientModel):
    _inherit = "sale.mass.cancel.orders"

    def action_mass_cancel(self):
        """The standard wizard cancels without the checks action_cancel() runs, so we
        run them here too."""
        # cancelled orders are skipped: the old path let some through with an invoice
        self.sale_order_ids.filtered(lambda order: order.state != "cancel")._check_cancel_allowed()
        return super().action_mass_cancel()
