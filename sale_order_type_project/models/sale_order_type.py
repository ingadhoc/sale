# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderType(models.Model):
    _inherit = "sale.order.type"

    project_id = fields.Many2one(
        comodel_name="project.project",
        domain=[("allow_billable", "=", True)],
        string="Project",
        help="Select to define the analytics account",
    )
