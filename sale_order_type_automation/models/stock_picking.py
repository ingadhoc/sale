##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_done(self):
        """
        On picking confirmation we check if invoice should be created
        """
        res = super().action_done()
        self.sudo().mapped('sale_id').run_invoicing_atomation()
        return res
