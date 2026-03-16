# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    project_id = fields.Many2one(
        compute="_compute_project_id",
        store=True,
        readonly=False,
        precompute=True,
    )

    @api.depends("type_id")
    def _compute_project_id(self):
        for order in self:
            if order.type_id and order.type_id.project_id:
                order.project_id = order.type_id.project_id
