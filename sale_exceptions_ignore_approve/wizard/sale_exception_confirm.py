# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api


class SaleExceptionConfirm(models.TransientModel):

    _inherit = 'sale.exception.confirm'

    @api.one
    def action_confirm(self):
        res = super(SaleExceptionConfirm, self).action_confirm()
        if self.ignore and not self._context.get('print_exceptions', False):
            return self.sale_id.action_confirm()
        return res
