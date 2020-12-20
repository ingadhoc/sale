##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def check_unapproved_partner_ok(self):
        self.ensure_one()
        if self.company_id.restrict_sales == 'yes':
            if self.partner_id.commercial_partner_id.\
                    partner_state != 'approved':
                return False
        return True

    def check_unapproved_partner_amount_ok(self):
        self.ensure_one()
        if self.company_id.restrict_sales == 'amount_depends':
            if (
                    self.partner_id.commercial_partner_id.
                    partner_state != 'approved' and
                    self.amount_total >= self.company_id.
                    restrict_sales_amount):
                return False
        return True
