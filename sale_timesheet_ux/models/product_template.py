from odoo import models, fields


class ProductTemplate(models.Model):

    _inherit = "product.template"

    create_from_project_id = fields.Many2one(
        'project.project',
        string="Create from project",
        help="If you choose a project, instead of creating a new project from"
        " scratch we will create a copy of this project")
