from odoo import models, fields


class ResUsers(models.Model):

    _inherit = 'res.users'

    default_sale_order_type_id = fields.Many2one(
        'sale.order.type',
        'Default Sale Order Type',
    )
