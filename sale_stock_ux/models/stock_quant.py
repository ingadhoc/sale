from odoo import models, fields


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    cost_currency_id = fields.Many2one(
        related='product_id.cost_currency_id',
        groups='stock.group_stock_manager',
    )
