from odoo import api, fields, models


class AllowBillableWizard(models.TransientModel):
    _name = "allow.billable.wizard"
    _description = "Confirmar cambio de valor de Allow Billable"

    project_id = fields.Many2one(
        "project.project", string="Project", default=lambda self: self.default_get_project_id()
    )
    has_linked_products = fields.Boolean(compute="_compute_has_linked_products")

    @api.depends("project_id")
    def _compute_has_linked_products(self):
        for wizard in self:
            project = wizard.project_id
            wizard.has_linked_products = bool(project and project._fetch_linked_products(project.ids, limit=1))

    @api.model
    def default_get_project_id(self):
        project = self.env["project.project"].search([("id", "=", self.env.context.get("project_id"))])
        return project

    def confirm_change(self):
        self.project_id.allow_billable = False
        return {"type": "ir.actions.act_window_close"}

    def cancel_change(self):
        self.project_id.allow_billable = True
        return {"type": "ir.actions.act_window_close"}
