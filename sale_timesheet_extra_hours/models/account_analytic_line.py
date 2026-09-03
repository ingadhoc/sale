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
        result = super()._timesheet_postprocess_values(values)
        base_fields_changed = any(f in values for f in ["unit_amount", "employee_id", "account_id"])
        extra_hour_changed = any(f in values for f in ["extra_hour", "extra_hour_type"])
        if not (base_fields_changed or extra_hour_changed):
            return result
        for timesheet in self.sudo():
            employee = timesheet.employee_id
            # In multi-company setups the active company (e.g. LLC/USD) may lack
            # exchange rates for the employee's home currency (e.g. UYU). Odoo's
            # COALESCE then falls back to rate=1 — treating UYU as USD. Use the
            # employee's company for rate lookup when it differs from the active one.
            rate_company = (
                employee.company_id
                if employee.company_id
                and employee.company_id != self.env.company
                and employee.currency_id != self.env.company.currency_id
                else self.env.company
            )
            needs_recompute = extra_hour_changed or (
                base_fields_changed and rate_company != self.env.company
            )
            if not needs_recompute:
                continue
            cost = timesheet._hourly_cost()
            amount = -timesheet.unit_amount * cost
            amount_converted = employee.currency_id._convert(
                amount,
                timesheet.account_id.currency_id or timesheet.currency_id,
                rate_company,
                timesheet.date,
            )
            result[timesheet.id].update({"amount": amount_converted})
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
