from odoo import Command
from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet
from odoo.tests import tagged

PROTECT_PARAM = "sale_timesheet_ux.protect_so_line"


@tagged("post_install", "-at_install")
class TestSaleTimesheetUx(TestCommonSaleTimesheet):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner_a.id,
                "order_line": [Command.create({"product_id": cls.product_order_timesheet3.id, "product_uom_qty": 5})],
            }
        )
        cls.order.action_confirm()
        cls.line = cls.order.order_line
        cls.project = cls.line.project_id
        cls.task = cls.line.task_id

    def _timesheet(self, **vals):
        return self.env["account.analytic.line"].create(
            {
                "name": "Work",
                "project_id": self.project.id,
                "task_id": self.task.id,
                "employee_id": self.employee_user.id,
                "unit_amount": 1,
                **vals,
            }
        )

    def test_protect_so_line_param(self):
        timesheet = self._timesheet()
        self.assertTrue(timesheet._is_not_billed())
        self.env["ir.config_parameter"].set_bool(PROTECT_PARAM, True)
        self.assertEqual(timesheet.so_line, self.line)
        self.assertFalse(timesheet._is_not_billed())

    def test_billed_timesheet_stays_billed(self):
        timesheet = self._timesheet()
        invoice = self.order._create_invoices()
        timesheet.reinvoice_move_id = invoice
        self.assertFalse(timesheet._is_not_billed())

    def test_order_project_is_reused(self):
        other_line = self.env["sale.order.line"].create(
            {
                "order_id": self.order.id,
                "product_id": self.product_order_timesheet3.id,
                "product_uom_qty": 1,
            }
        )
        self.assertEqual(other_line._timesheet_create_project(), self.project)

    def test_untick_billable_keeps_customer_and_order(self):
        self.project.write({"allow_billable": True})
        self.assertEqual(self.task.order_id, self.order)
        timesheet = self._timesheet(so_line=self.line.id, is_so_line_edited=True)
        action = self.project.change_allow_billable()
        self.env["allow.billable.wizard"].browse(action["res_id"]).confirm_change()
        self.assertFalse(self.project.allow_billable)
        self.assertEqual(self.project.partner_id, self.partner_a)
        self.assertEqual(self.task.order_id, self.order)
        self.assertIn(self.task, self.order.tasks_ids)
        self.assertEqual(timesheet.so_line, self.line)
