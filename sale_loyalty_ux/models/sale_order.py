##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):

    _inherit = "sale.order"
    def _program_check_compute_points(self, programs):
        res = super()._program_check_compute_points(programs)
        for r in res:
            domain = r._get_valid_sale_order()
            if not res[r].get('error') and domain:
                if self not in self.env['sale.order'].search(domain):
                    res[r] = {'error': "SaleOrder not matching"}
        return res
