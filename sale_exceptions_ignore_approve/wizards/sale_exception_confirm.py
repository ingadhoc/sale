##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleExceptionConfirm(models.TransientModel):
    _inherit = 'sale.exception.confirm'

    def action_confirm(self):
        res = super().action_confirm()
        if self.ignore:
            return self.related_model_id.action_confirm()
        return res
