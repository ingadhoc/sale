##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def check_credit_limit_ok(self):
        self.ensure_one()
        if self.partner_credit_warning:
            return False
        return True
