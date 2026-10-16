from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    sale_order_id = fields.Many2one(index="btree_not_null")
