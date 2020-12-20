from odoo import api, models


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    @api.model
    def _default_type_id(self):
        return self.env.user.default_sale_order_type_id or super()._default_type_id()
