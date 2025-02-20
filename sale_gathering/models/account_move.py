from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        down_payment_lines = self.line_ids.filtered(
            lambda line: line.is_downpayment and line.sale_line_ids.order_id.is_gathering
        )

        sale_lines_data = []
        for move_line in down_payment_lines:
            for sale_line in move_line.sale_line_ids:
                sale_lines_data.append((sale_line, sale_line.tax_id, sale_line.price_unit))

        res = super().action_post()

        for sale_line, tax_id, price_unit in sale_lines_data:
            sale_line.write(
                {
                    "tax_id": tax_id,
                    "price_unit": price_unit,
                }
            )
        return res
