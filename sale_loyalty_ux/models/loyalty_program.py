##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import ast

from odoo import fields, models
from odoo.fields import Domain


class LoyaltyProgram(models.Model):
    _inherit = "loyalty.program"

    sale_domain = fields.Char(default="[]")
    not_applicable_message = fields.Char(
        string="Message When the Promotion Does Not Apply",
        translate=True,
        help="Message shown to the user when the sales order does not match the sales domain. "
        "Use it to explain why the program does not apply and what to do to make it apply. "
        "If empty, a generic message is used.",
    )

    def _get_valid_sale_order(self):
        domain = []
        if self.sale_domain and self.sale_domain != "[]":
            domain = Domain.AND([domain, ast.literal_eval(self.sale_domain)])
            return domain
        return False
