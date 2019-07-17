##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        if self.order_id.type_id.analytic_tag_ids:
            self.analytic_tag_ids = self.order_id.type_id.analytic_tag_ids
        return super().product_id_change()
