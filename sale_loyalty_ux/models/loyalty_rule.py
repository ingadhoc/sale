##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import ast

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class LoyaltyRule(models.Model):
    _inherit = "loyalty.rule"

    @api.constrains("product_domain")
    def _check_product_domain(self):
        for rule in self:
            if rule.product_domain and rule.product_domain != "[]":
                for condition in Domain(ast.literal_eval(rule.product_domain)).iter_conditions():
                    if condition.operator in ("=", "!=") and isinstance(condition.value, (list, tuple)):
                        raise ValidationError(
                            self.env._(
                                "Invalid domain syntax: operator '%(operator)s' cannot be used "
                                "with a list value %(value)s. Use 'in' or 'not in' instead.",
                                operator=condition.operator,
                                value=condition.value,
                            )
                        )
