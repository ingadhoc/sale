from odoo import models, fields


class SaleOrderTypology(models.Model):

    _inherit = 'sale.order.type'
    _order = "sequence asc"

    sequence = fields.Integer(
        'Sequence',
        required=True,
        default=10,
    )

    analytic_tag_ids = fields.Many2many(
        'account.analytic.tag',
        string='Analytic Tags',
        help="Default analytic tags that will be used on new sale order lines",
    )
