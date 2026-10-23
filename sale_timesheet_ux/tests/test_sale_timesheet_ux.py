from odoo import Command
from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet
from odoo.tests import new_test_user, tagged

PROTECT_PARAM = "sale_timesheet_ux.protect_so_line"


@tagged("post_install", "-at_install")
class TestSaleTimesheetUx(TestCommonSaleTimesheet):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.order = cls._create_order(cls.partner_a)
        cls.line = cls.order.order_line
        cls.project = cls.line.project_id
        cls.task = cls.line.task_id

    @classmethod
    def _create_order(cls, partner, **vals):
        order = cls.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [Command.create({"product_id": cls.product_order_timesheet3.id, "product_uom_qty": 5})],
                **vals,
            }
        )
        order.action_confirm()
        return order

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

    def _switch_billable_off(self):
        action = self.project.change_allow_billable()
        self.env["allow.billable.wizard"].browse(action["res_id"]).confirm_change()

    def test_protect_so_line_param(self):
        timesheet = self._timesheet()
        self.assertEqual(timesheet.so_line, self.line)
        self.assertTrue(timesheet._is_not_billed())
        self.env["ir.config_parameter"].set_bool(PROTECT_PARAM, True)
        self.assertFalse(timesheet._is_not_billed())
        self.env["ir.config_parameter"].set_bool(PROTECT_PARAM, False)
        self.assertTrue(timesheet._is_not_billed())

    def test_billed_timesheet_stays_billed(self):
        # the protection relies on the billed check of the core
        timesheet = self._timesheet()
        timesheet.reinvoice_move_id = self.order._create_invoices()
        self.assertFalse(timesheet._is_not_billed())
        self.env["ir.config_parameter"].set_bool(PROTECT_PARAM, True)
        self.assertFalse(timesheet._is_not_billed())

    def test_order_project_is_reused(self):
        projects = self.env["project.project"].search_count([])
        order = self._create_order(self.partner_a, project_id=self.project.id)
        self.assertEqual(order.order_line.task_id.project_id, self.project)
        self.assertEqual(self.env["project.project"].search_count([]), projects)

    def test_billable_off_keeps_customer_and_order(self):
        timesheet = self._timesheet(so_line=self.line.id, is_so_line_edited=True)
        self._switch_billable_off()
        self.assertFalse(self.project.allow_billable)
        self.assertEqual(self.project.partner_id, self.partner_a)
        self.assertEqual(self.project.sale_line_id, self.line)
        self.assertEqual(self.task.partner_id, self.partner_a)
        self.assertEqual(self.task.sale_line_id, self.line)
        self.assertIn(self.task, self.order.tasks_ids)
        self.assertEqual(timesheet.so_line, self.line)

    def test_billable_on_again_links_tasks_to_order(self):
        self._switch_billable_off()
        self.assertFalse(self.task.order_id)
        self.project.write({"allow_billable": True})
        self.assertEqual(self.task.order_id, self.order)

    def test_cancel_keeps_billable(self):
        action = self.project.change_allow_billable()
        self.env["allow.billable.wizard"].browse(action["res_id"]).cancel_change()
        self.assertTrue(self.project.allow_billable)

    def test_order_tasks_include_related_order(self):
        linked, template = self.env["project.task"].create(
            [
                {"name": "Linked", "project_id": self.project.id, "order_id": self.order.id, "sale_line_id": False},
                {
                    "name": "Template",
                    "project_id": self.project.id,
                    "order_id": self.order.id,
                    "sale_line_id": False,
                    "is_template": True,
                },
            ]
        )
        self.assertFalse(linked.sale_line_id)
        self.order.invalidate_recordset(["tasks_ids", "tasks_count", "closed_task_count"])
        self.assertIn(linked, self.order.tasks_ids)
        self.assertNotIn(template, self.order.tasks_ids)
        self.assertEqual(self.order.tasks_count, len(self.order.tasks_ids))
        self.assertEqual(self.order.closed_task_count, 0)
        linked.state = "1_done"
        self.order.invalidate_recordset(["tasks_ids", "tasks_count", "closed_task_count"])
        self.assertEqual(self.order.closed_task_count, 1)

    def test_portal_can_search_task_order(self):
        portal = new_test_user(self.env, login="portal_ux", groups="base.group_portal")
        tasks = self.env["project.task"].with_user(portal).search([("order_id", "in", self.order.ids)])
        self.assertFalse(tasks)

    def test_count_timesheets_to_relink(self):
        self.assertEqual(self.task.count_timesheets_to_relink(), 0)
        self._timesheet()
        self._timesheet(so_line=self.line.id, is_so_line_edited=True)
        billed = self._timesheet()
        billed.reinvoice_move_id = self.order._create_invoices()
        self.assertEqual(self.task.count_timesheets_to_relink(), 1)
        self.env["ir.config_parameter"].set_bool(PROTECT_PARAM, True)
        self.assertEqual(self.task.count_timesheets_to_relink(), 0)

    def test_wizard_warns_when_products_are_linked(self):
        def wizard():
            action = self.project.change_allow_billable()
            return self.env["allow.billable.wizard"].browse(action["res_id"])

        self.assertFalse(wizard().has_linked_products)
        self.env["product.product"].create(
            {
                "name": "Service in a fixed project",
                "type": "service",
                "service_type": "timesheet",
                "service_tracking": "task_global_project",
                "project_id": self.project.id,
            }
        )
        self.assertTrue(wizard().has_linked_products)
