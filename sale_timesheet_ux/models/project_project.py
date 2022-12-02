from odoo import models


class ProjectProject(models.Model):

    _inherit = 'project.project'

    def write(self, values):
        """ Ver readme de modulo item "c"
        # TODO this should go as PR to odoo """
        for rec in self.task_ids:
            if self.allow_billable:
                rec.order_id = rec.sale_order_id
        if 'allow_billable' in values and not values.get('allow_billable'):
            self = self.with_context(write_allow_billiable=True)
        res = super().write(values)
        return res
