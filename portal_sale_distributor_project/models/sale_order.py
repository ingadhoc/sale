##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    tasks_ids = fields.Many2many(
        groups="project.group_project_user,portal_sale_distributor.group_portal_backend_distributor"
    )
    tasks_count = fields.Integer(
        groups="project.group_project_user,portal_sale_distributor.group_portal_backend_distributor"
    )
    closed_task_count = fields.Integer(
        groups="project.group_project_user,portal_sale_distributor.group_portal_backend_distributor"
    )
