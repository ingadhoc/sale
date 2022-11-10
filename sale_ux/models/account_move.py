##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class AccountMove(models.Model):

    _inherit = 'account.move'

    # dejamos este campo por si alguien lo usaba y ademas lo re usamos abajo
    sale_order_ids = fields.Many2many(
        'sale.order',
        compute='_compute_sale_orders'
    )
    # en la ui agregamos este que seria mejor a nivel performance
    has_sales = fields.Boolean(
        string='Has Sales?',
        compute='_compute_has_sales'
    )

    def _compute_sale_orders(self):
        for rec in self:
            rec.sale_order_ids = rec.invoice_line_ids.mapped(
                'sale_line_ids.order_id')

    def _compute_has_sales(self):
        moves = self.filtered(lambda move: move.is_sale_document())
        (self - moves).has_sales = False
        for rec in moves:
            rec.has_sales = any(line for line in rec.invoice_line_ids.mapped('sale_line_ids'))
