# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from openerp import api, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def do_transfer(self):
        """
        On picking confirmation we check if invoice should be created
        """
        res = super(StockPicking, self).do_transfer()
        self.mapped('sale_id').run_invoicing_atomation()
        return res
