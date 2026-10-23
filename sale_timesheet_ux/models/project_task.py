from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    order_id = fields.Many2one(
        "sale.order",
        "Related Sales Order",
        store=True,
        index="btree_not_null",
        help="Sales order to which the task is linked.",
    )

    @property
    def TASK_PORTAL_READABLE_FIELDS(self):
        return super().TASK_PORTAL_READABLE_FIELDS | {"order_id"}

    def _get_timesheet(self):
        recs = super()._get_timesheet()
        if self.env.context.get("write_allow_billiable"):
            recs = recs.filtered(lambda x: not x.is_so_line_edited)
        return recs

    def _compute_partner_id(self):
        for task in self:
            task_partner_id = task.partner_id or task.project_id.partner_id or task.sale_order_id.partner_id
            super()._compute_partner_id()
            task.partner_id = task_partner_id

    def _compute_sale_line(self):
        for task in self:
            sale_line = (
                task.sale_line_id
                or task.parent_id.sale_line_id
                or task.project_id.sale_line_id
                or task.milestone_id.sale_line_id
            )
            super()._compute_sale_line()
            if not task.sale_line_id or task.sale_line_id != sale_line:
                task.sale_line_id = sale_line

    def count_timesheets_to_relink(self):
        """Timesheet lines whose sales order item is recalculated when the one of the task changes."""
        self.ensure_one()
        return len(
            self.timesheet_ids.filtered(
                # "validated" is defined by timesheet_grid (Enterprise), which is not a dependency
                lambda t: not t.is_so_line_edited
                and t._is_not_billed()
                and not ("validated" in t._fields and t.validated)
            )
        )
