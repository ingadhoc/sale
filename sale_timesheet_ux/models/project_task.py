from odoo import models, fields


class ProjectTask(models.Model):

    _inherit = 'project.task'

    order_id = fields.Many2one('sale.order', 'Related Sales Order', store=True, help="Sales order to which the task is linked.")

    def _get_timesheet(self):
        recs = super()._get_timesheet()
        if self._context.get('write_allow_billiable'):
            recs = recs.filtered(lambda x: not x.is_so_line_edited)
        return recs

    def _compute_sale_order_id(self):
        # Store allow_billable task's state to mantain the relation
        # between the task with the SO that originated it when allow_billable is changed in project
        billable_condition = {x: x.allow_billable for x in self}
        self.allow_billable = True
        super()._compute_sale_order_id()
        for k, v in billable_condition.items():
            k.allow_billable = v

    def _compute_sale_line(self):
        # Override this method to combine the behavior between sale_project and sale_timesheet
        # so the change of value of "allow_billable" to True doesn't unlink the sale_line_id of the task 
        # with the SO that originated it 
        billable_tasks = self.filtered('allow_billable')
        for task in billable_tasks:
            if not task.sale_line_id:
                # if the display_project_id is set then it means the task is classic task or a subtask with another project than its parent.
                task.sale_line_id = task.display_project_id.sale_line_id or task.parent_id.sale_line_id or task.project_id.sale_line_id or task.milestone_id.sale_line_id
            # check sale_line_id and customer are coherent
            if task.sale_line_id.order_partner_id.commercial_partner_id != task.partner_id.commercial_partner_id:
                task.sale_line_id = False
