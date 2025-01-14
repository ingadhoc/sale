from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"
    approve_picking = fields.Boolean(string="Prepayment in current account", required=False, tracking=True, copy=False)
