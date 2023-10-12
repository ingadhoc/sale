from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        down_payment_line = self.line_ids.filtered(lambda line: line.is_downpayment and line.sale_line_ids.order_id.is_gathering)
        if down_payment_line:
            tax_id = down_payment_line.sale_line_ids.tax_id
            price_unit = down_payment_line.sale_line_ids.price_unit
        res = super(AccountMove, self).action_post()
        if down_payment_line:
            for line in down_payment_line:
                line.sale_line_ids.tax_id = tax_id
                line.sale_line_ids.price_unit = price_unit
        return res
