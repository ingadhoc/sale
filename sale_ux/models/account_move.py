##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # Evaluar en proximas versiones si Odoo lo resuelve
    def action_post(self):
        res = super(AccountMove, self).action_post()
        downpayment_lines = self.line_ids.sale_line_ids.filtered(lambda l: l.is_downpayment and not l.display_type)
        for downpayment_line in downpayment_lines:
            # When change currency in downpayment
            if self.currency_id != downpayment_line.currency_id:
                downpayment_line.price_unit = self.currency_id._convert(
                    downpayment_line.price_unit,
                    downpayment_line.currency_id,
                    self.company_id,
                    self.invoice_date or fields.Date.today(),
                )
        return res
