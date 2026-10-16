from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    offline_order_id = fields.Many2one(
        "sale.offline.order",
        readonly=True,
        copy=False,
        index="btree_not_null",
        ondelete="restrict",
    )

    _offline_order_unique = models.Constraint(
        "UNIQUE(offline_order_id)",
        "This offline order was already converted into a sale order.",
    )
