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
        if self.ignore and self._context.get('print_exceptions', False):
            self.sale_id.ignore_exception_print = True
            self.ignore = False
        return super(SaleExceptionConfirm, self).action_confirm()
