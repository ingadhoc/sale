##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    lost_qty = fields.Float(string="Unsold Quantity", readonly=True)
    lost_reason_id = fields.Many2one("sale.order.line.lost.reason", string="Unsold Reason", readonly=True)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res["lost_qty"] = "CASE WHEN l.product_id IS NOT NULL THEN SUM(l.lost_qty * u.factor / u2.factor) ELSE 0 END"
        res["lost_reason_id"] = "l.lost_reason_id"
        return res

    def _group_by_sale(self):
        return (
            super()._group_by_sale()
            + """,
            l.lost_reason_id"""
        )
