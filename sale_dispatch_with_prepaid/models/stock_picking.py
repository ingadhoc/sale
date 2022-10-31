from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _check_sale_paid(self):
        if self.sale_id and self.sale_id.approve_picking:
            return True
        return super()._check_sale_paid()
