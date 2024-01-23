##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import ast

from odoo import fields, models
from odoo.osv import expression


class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    sale_domain = fields.Char(default="[]")

    def _get_valid_sale_order(self):
        domain = []
        if self.sale_domain and self.sale_domain != '[]':
            domain = expression.AND([domain, ast.literal_eval(self.sale_domain)])
            return domain
        return False
