from odoo import models, fields


class ProjectTask(models.Model):

    _inherit = 'project.task'

    order_id = fields.Many2one('sale.order', 'Related Sales Order', store=True, help="Sales order to which the task is linked.")

    def _get_timesheet(self):
        recs = super()._get_timesheet()
        if self._context.get('write_allow_billiable'):
            recs = recs.filtered(lambda x: not x.is_so_line_edited)
        return recs
