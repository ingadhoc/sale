from odoo import models, fields, api

class AllowBillableWizard(models.TransientModel):
    _name = 'allow.billable.wizard'
    _description = 'Confirmar cambio de valor de Allow Billable'

    project_id = fields.Many2one('project.project', string='Project', default=lambda self: self.default_get_project_id())

    @api.model
    def default_get_project_id(self):
        project = self.env['project.project'].search([('id', '=', self.env.context.get('project_id'))])
        return project

    def confirm_change(self):
        self.project_id.allow_billable = False
        return {'type': 'ir.actions.act_window_close'}

    def cancel_change(self):
        self.project_id.allow_billable = True
        return {'type': 'ir.actions.act_window_close'}
