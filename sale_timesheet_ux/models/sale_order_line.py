from odoo import models


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    def _timesheet_create_project(self):
        self.ensure_one()
        account = self.order_id.analytic_account_id
        if account:
            project = self.env[
                'project.project'].search([(
                    'analytic_account_id', '=', account.id)])
            if len(project) == 1:
                return project
        return super()._timesheet_create_project()
