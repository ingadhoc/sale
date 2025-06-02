from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_abandoned_cart = fields.Boolean(compute_sudo=True)
