# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    to_refund_so = fields.Boolean(
        default=True,
    )
