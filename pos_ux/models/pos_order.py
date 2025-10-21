from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _process_saved_order(self, draft):
        if self.session_id.invoice_contingency and self.to_invoice:
            self.to_invoice = False
            result = super()._process_saved_order(draft)
            self.to_invoice = True
            return result
        return super()._process_saved_order(draft)
