##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleExceptionConfirm(models.TransientModel):
    _inherit = "sale.exception.confirm"

    def action_confirm(self):
        """Ignore through the order, which now confirms it as well.

        Otherwise the wizard would confirm an order that is already confirmed.
        The print flow is left alone: it only ignores the print exceptions.
        """
        if self.ignore and not self.env.context.get("print_exceptions", False):
            self.related_model_id.action_ignore_exceptions()
            self.ignore = False
        return super().action_confirm()
