from odoo import fields
from odoo.tests.common import TransactionCase


class TestExtraHourCost(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Extra Hours Employee",
                "hourly_cost": 100.0,
                "day_extra_hour_coef": 20.0,
                "night_extra_hour_coef": 50.0,
            }
        )
        product = cls.env["product.product"].create(
            {
                "name": "Timesheet service",
                "type": "service",
                "invoice_policy": "delivery",
                "service_type": "timesheet",
            }
        )
        order = cls.env["sale.order"].create(
            {
                "partner_id": cls.env["res.partner"].create({"name": "Extra Hours Customer"}).id,
                "order_line": [fields.Command.create({"product_id": product.id, "product_uom_qty": 10})],
            }
        )
        order.action_confirm()
        cls.sale_line = order.order_line

    def _project(self, employee_map=None):
        return self.env["project.project"].create(
            {
                "name": "Extra Hours Project",
                "allow_billable": True,
                "allow_timesheets": True,
                "partner_id": self.sale_line.order_partner_id.id,
                "sale_line_id": self.sale_line.id,
                "sale_line_employee_ids": employee_map and [fields.Command.create(employee_map)] or [],
            }
        )

    def _timesheet(self, project, **values):
        return self.env["account.analytic.line"].create(
            {
                "name": "Work",
                "project_id": project.id,
                "employee_id": self.employee.id,
                "unit_amount": 2.0,
                "date": self.today,
                **values,
            }
        )

    def test_fixed_rate_cost_follows_extra_hour_type(self):
        """Given a fixed rate project and an employee with day/night extra hour
        coefficients, when the timesheet is marked as extra hour and its type
        changes, then cost and amount are recalculated on every step.
        """
        timesheet = self._timesheet(self._project())
        self.assertEqual(timesheet.project_id.pricing_type, "fixed_rate")
        steps = [
            ("regular hour uses the employee hourly cost", {}, 100.0),
            ("marking an extra hour by day applies the day coefficient", {"extra_hour": True}, 120.0),
            ("switching to night applies the night coefficient", {"extra_hour_type": "night"}, 150.0),
            ("unmarking the extra hour goes back to the hourly cost", {"extra_hour": False}, 100.0),
        ]
        for label, values, expected_cost in steps:
            with self.subTest(label):
                timesheet.write(values)
                self.assertEqual(timesheet.cost, expected_cost)
                self.assertEqual(timesheet.amount, -2.0 * expected_cost)

    def test_employee_rate_cost_comes_from_the_project_map(self):
        """Given an employee rate project whose map has its own regular, day and
        night costs, when a timesheet is created for each kind of hour, then the
        cost is the one in the map and not the one on the employee.
        """
        project = self._project(
            {
                "employee_id": self.employee.id,
                "sale_line_id": self.sale_line.id,
                "cost": 110.0,
                "cost_day_extra_hour": 130.0,
                "cost_night_extra_hour": 160.0,
            }
        )
        self.assertEqual(project.pricing_type, "employee_rate")
        cases = [
            ("regular hour", {}, 110.0),
            ("extra hour by day", {"extra_hour": True, "extra_hour_type": "day"}, 130.0),
            ("extra hour by night", {"extra_hour": True, "extra_hour_type": "night"}, 160.0),
        ]
        for label, values, expected_cost in cases:
            with self.subTest(label):
                timesheet = self._timesheet(project, **values)
                self.assertEqual(timesheet.cost, expected_cost)
                self.assertEqual(timesheet.amount, -2.0 * expected_cost)
