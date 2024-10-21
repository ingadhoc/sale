from odoo import models


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"
    
    def _show_discount(self):
        self = self.sudo()
        return super()._show_discount()
