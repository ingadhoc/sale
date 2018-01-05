from openerp import models, fields


class SaleOrderTypology(models.Model):

    _inherit = 'sale.order.type'
    _order = "sequence asc"

    sequence = fields.Integer(
        'Sequence',
        required=True,
        default=10)
