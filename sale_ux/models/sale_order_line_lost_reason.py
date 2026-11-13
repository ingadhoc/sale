##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class SaleOrderLineLostReason(models.Model):
    _name = "sale.order.line.lost.reason"
    _description = "Sale Order Line Lost Reason"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint("unique (name)", "This lost reason already exists.")
