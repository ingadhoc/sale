from odoo import fields, models


class SaleOfflineOrderError(models.Model):
    """Conversion failures, kept apart so the raw inbox is never updated."""

    _name = "sale.offline.order.error"
    _description = "Offline Sale Order Conversion Error"
    _order = "id desc"

    offline_order_id = fields.Many2one("sale.offline.order", required=True, index=True, ondelete="cascade")
    message = fields.Text(required=True)
