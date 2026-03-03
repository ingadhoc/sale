##############################################################################
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _is_downpayment(self):
        self.ensure_one()
        result = super()._is_downpayment()

        if result:
            return result

        sale_lines = self.line_ids.sale_line_ids
        if sale_lines:
            orders = sale_lines.order_id
            if orders.filtered("is_gathering"):
                has_downpayment = any(line.is_downpayment for line in sale_lines)
                all_downpayment_or_delivery = all(line.is_downpayment or line.is_delivery for line in sale_lines)
                if has_downpayment and all_downpayment_or_delivery:
                    return True

        return False
