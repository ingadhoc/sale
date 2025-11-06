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

    cost = fields.Float()

    def _timesheet_postprocess_values(self, values):
        """Override to trigger cost recalculation when extra_hour fields change"""
        result = super()._timesheet_postprocess_values(values)
        # Add extra_hour and extra_hour_type to the list of fields that trigger cost recalculation
        if any(field_name in values for field_name in ["extra_hour", "extra_hour_type"]):
            sudo_self = self.sudo()
            for timesheet in sudo_self:
                cost = timesheet._hourly_cost()
                amount = -timesheet.unit_amount * cost
                amount_converted = timesheet.employee_id.currency_id._convert(
                    amount, timesheet.account_id.currency_id or timesheet.currency_id, self.env.company, timesheet.date
                )
                result[timesheet.id].update(
                    {
                        "amount": amount_converted,
                    }
                )
        return result

    def _hourly_cost(self):
        self.ensure_one()
        if self.project_id.pricing_type == "fixed_rate":
            if self.extra_hour:
                if self.extra_hour_type == "day":
                    self.cost = self.employee_id.day_extra_hour_cost
                else:
                    self.cost = self.employee_id.night_extra_hour_cost
            else:
                self.cost = self.employee_id.hourly_cost or 0.0
            return self.cost
        if self.project_id.pricing_type == "employee_rate":
            mapping_entry = self._get_employee_mapping_entry()
            if mapping_entry:
                if self.extra_hour:
                    if self.extra_hour_type == "day":
                        self.cost = mapping_entry.cost_day_extra_hour
                    else:
                        self.cost = mapping_entry.cost_night_extra_hour
                else:
                    self.cost = mapping_entry.cost or 0.0
            return self.cost
        return super()._hourly_cost()
