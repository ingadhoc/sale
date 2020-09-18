##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_protected_fields(self):
        """
        we use this to skip change the qty for the delivery line with cost zero
        """
        skip_validation = self._context.get('skip_validation', '')
        if not skip_validation:
            return super()._get_protected_fields()
        fields = super()._get_protected_fields()
        fields.remove(skip_validation)
        return fields
