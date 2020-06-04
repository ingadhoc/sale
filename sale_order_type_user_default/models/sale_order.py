from odoo import models, fields


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    type_id = fields.Many2one(
        'sale.order.type',
        default=lambda so: so.env.user.default_sale_order_type_id or False,
    )
