from odoo import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    extra_hour = fields.Boolean(
        "Extra Hour?",
    )

    extra_hour_type = fields.Selection(
        [("day", "Day"), ("night", "Night"), ("holiday", "Holiday")],
        default="day",
    )

    def _hourly_cost(self):
        if self.project_id.pricing_type == "fixed_rate":
            self.ensure_one()
            if self.extra_hour:
                if self.extra_hour_type == "day":
                    return self.employee_id.day_extra_hour_cost
                else:
                    return self.employee_id.night_extra_hour_cost
            else:
                return self.employee_id.hourly_cost or 0.0
        if self.project_id.pricing_type == "employee_rate":
            mapping_entry = self._get_employee_mapping_entry()
            if mapping_entry:
                if self.extra_hour:
                    if self.extra_hour_type == "day":
                        return mapping_entry.cost_day_extra_hour
                    else:
                        return mapping_entry.cost_night_extra_hour
                else:
                    return mapping_entry.cost or 0.0
        return super()._hourly_cost()
