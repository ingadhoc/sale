from odoo import models, fields


class ProjectTask(models.Model):

    _inherit = 'project.task'

    order_id = fields.Many2one('sale.order', 'Related Sales Order', store=True, help="Sales order to which the task is linked.")

    def _get_timesheet(self):
        recs = super()._get_timesheet()
        if self._context.get('write_allow_billiable'):
            recs = recs.filtered(lambda x: not x.is_so_line_edited)
        return recs

    def _compute_partner_id(self):
        for task in self:
            task_partner_id = task.partner_id or task.project_id.partner_id or task.sale_order_id.partner_id
            super()._compute_partner_id()
            task.partner_id = task_partner_id

    def _compute_sale_line(self):
        for task in self:
            sale_line = task.sale_line_id or task.parent_id.sale_line_id or task.project_id.sale_line_id or task.milestone_id.sale_line_id
            super()._compute_sale_line()
            if not task.sale_line_id or task.sale_line_id != sale_line:
                task.sale_line_id = sale_line
