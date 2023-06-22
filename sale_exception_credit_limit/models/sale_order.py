##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = "sale.order"


    def _compute_partner_credit_warning(self):
        for order in self:
            order.with_company(order.company_id)
            order.partner_credit_warning = ''
            show_warning = order.state in ('draft', 'sent') and \
                           order.company_id.account_use_credit_limit
            if show_warning:
                updated_credit = order.partner_id.commercial_partner_id.credit_with_confirmed_orders + (order.amount_total * order.currency_rate)
                order.partner_credit_warning = self.env['account.move']._build_credit_warning_message(
                    order, updated_credit)

    def check_credit_limit_ok(self):
        self.ensure_one()
        if self.partner_credit_warning:
            return False
        return True
