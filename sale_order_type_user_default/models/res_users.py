from openerp import models, fields


class res_users(models.Model):

    _inherit = 'res.users'

    default_sale_order_type_id = fields.Many2one(
        'sale.order.type',
        'Default Sale Order Type'
    )
