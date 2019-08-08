##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    sale_id = fields.Many2one(
        related='group_id.sale_id',
    )
