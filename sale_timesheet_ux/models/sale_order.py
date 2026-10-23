from odoo import api, models

from odoo.addons.project.models.project_task import CLOSED_STATES


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.depends("order_line.product_id.project_id")
    def _compute_tasks_ids(self):
        super()._compute_tasks_ids()
        tasks_per_so = self.env["project.task"]._read_group(
            domain=[
                ("order_id", "in", self.ids),
                ("is_template", "=", False),
                ("project_id", "!=", False),
                ("has_template_ancestor", "=", False),
            ],
            groupby=["order_id", "state"],
            aggregates=["id:recordset"],
        )
        for order, state, tasks in tasks_per_so:
            new_tasks = tasks - order.tasks_ids
            order.tasks_ids += new_tasks
            order.tasks_count += len(new_tasks)
            order.closed_task_count += len(new_tasks) if state in CLOSED_STATES else 0
