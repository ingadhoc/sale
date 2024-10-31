##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    number_sale_order_line = fields.Boolean(compute="_compute_number_sale_order_line")

    def _compute_number_sale_order_line(self):
        number_sale_order_line = self.env["ir.config_parameter"].sudo().get_param('sale_order_line_number.number_sale_order_line', False)
        self.number_sale_order_line = number_sale_order_line
