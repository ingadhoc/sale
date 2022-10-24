from odoo import models


class ProjectTask(models.Model):

    _inherit = 'project.task'

    def _get_timesheet(self):
        recs = super()._get_timesheet()
        if self._context.get('write_allow_billiable'):
            recs = recs.filtered(lambda x: not x.is_so_line_edited)
        return recs
