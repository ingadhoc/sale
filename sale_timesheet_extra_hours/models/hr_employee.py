# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    day_extra_hour_coef = fields.Float("Coefficient of an extra hour by day", groups="hr.group_hr_user")
    night_extra_hour_coef = fields.Float("Coefficient of an extra hour by night", groups="hr.group_hr_user")
    day_extra_hour_cost = fields.Monetary(
        "Cost of an extra hour by day",
        currency_field="currency_id",
        groups="hr.group_hr_user",
        compute="_compute_extra_hour_cost",
        readonly=True,
    )
    night_extra_hour_cost = fields.Monetary(
        "Cost of an extra hour by night",
        currency_field="currency_id",
        groups="hr.group_hr_user",
        compute="_compute_extra_hour_cost",
        readonly=True,
    )

    def _compute_extra_hour_cost(self):
        self.day_extra_hour_cost = self.hourly_cost * (self.day_extra_hour_coef + 100) / 100
        self.night_extra_hour_cost = self.hourly_cost * (self.night_extra_hour_coef + 100) / 100
