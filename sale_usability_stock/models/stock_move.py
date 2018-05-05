# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    sale_id = fields.Many2one(
        related='procurement_id.sale_line_id.order_id',
        readonly=True,
    )
