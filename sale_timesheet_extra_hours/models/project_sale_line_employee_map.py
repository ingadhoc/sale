# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectProductEmployeeMap(models.Model):
    _inherit = "project.sale.line.employee.map"

    cost_day_extra_hour = fields.Monetary(
        currency_field="cost_currency_id", groups="project.group_project_manager,hr.group_hr_user"
    )
    cost_night_extra_hour = fields.Monetary(
        currency_field="cost_currency_id", groups="project.group_project_manager,hr.group_hr_user"
    )

    @api.onchange("employee_id")
    def extra_hour_cost(self):
        self.cost_day_extra_hour = self.employee_id.day_extra_hour_cost
        self.cost_night_extra_hour = self.employee_id.night_extra_hour_cost
