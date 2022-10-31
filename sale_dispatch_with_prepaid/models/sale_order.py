from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    approve_picking = fields.Boolean(
        string="Prepayment in current account", required=False, tracking=True, copy=False)
