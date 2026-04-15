##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    reinvoiced_sale_order_id = fields.Many2one(
        groups="sales_team.group_sale_salesman,portal_sale_distributor.group_portal_backend_distributor"
    )


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
