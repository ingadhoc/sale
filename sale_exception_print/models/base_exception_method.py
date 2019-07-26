##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class BaseExceptionMethod(models.AbstractModel):
    _inherit = 'base.exception.method'

    def _rule_domain(self):
        """Filter exception.rules.
        By default, only the rules with the correct model
        will be used.
        """
        domain = super()._rule_domain()
        if self._context.get('print_exceptions', False) and \
                self._name in ['sale.order', 'sale.order.line']:
            domain += [('block_print', '=', True)]
        return domain
