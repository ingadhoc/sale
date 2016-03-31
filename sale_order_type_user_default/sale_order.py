from openerp import models, api, fields


class sale_order(models.Model):

    _inherit = 'sale.order'

    @api.model
    def _get_order_type(self):
        res = super(sale_order, self)._get_order_type()
        user = self.env.user
        if user.default_sale_order_type_id:
            res = user.default_sale_order_type_id
        return res

    type_id = fields.Many2one(
        'sale.order.type',
        default=_get_order_type)
