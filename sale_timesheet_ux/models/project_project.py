from odoo import models, _


class ProjectProject(models.Model):

    _inherit = 'project.project'

    def write(self, values):
        """ Ver readme de modulo item "c"
        # TODO this should go as PR to odoo """
        if 'allow_billable' in values and not values.get('allow_billable'):
            self = self.with_context(write_allow_billiable=True)
        res = super().write(values)
        if 'allow_billable' in values:
            for rec in self:
                if rec.allow_billable:
                    for task in rec.task_ids:
                        task.order_id = task.sale_order_id
        return res

    def _compute_partner_id(self):
        for project in self:
            project_partner_id = project.partner_id or project.analytic_account_id.partner_id or project.sale_order_id.partner_id
            super()._compute_partner_id()
            project.partner_id = project_partner_id

    def change_allow_billable(self):
        if self.allow_billable == True:
            wiz = self.env['allow.billable.wizard'].create({'project_id': self.id})
            return {
                'name': _('Project'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [(self.env.ref('sale_timesheet_ux.change_allow_billable_wizzard').id, 'form')],
                'res_model': 'allow.billable.wizard',
                'res_id': wiz.id,
                'target': 'new',
            }
