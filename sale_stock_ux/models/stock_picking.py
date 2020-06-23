from odoo import models, fields


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    observations = fields.Text(
    )
