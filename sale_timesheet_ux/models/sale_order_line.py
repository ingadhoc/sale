from odoo import models, api


class SaleOrderLine(models.Model):

    _inherit = "sale.order.line"

    @api.multi
    def _timesheet_service_generation(self):
        """ If lines 'task_new_project' or 'project_only', first create a
        project from the template and relate to the sale.order and then run
        all the service generation (this last will use the new project).
        """
        so_lines = self.filtered(
            lambda x: x.is_service and x.product_id.service_tracking in
            ['task_new_project', 'project_only'] and
            not x.order_id.analytic_account_id)
        if so_lines:
            so_lines[0].generate_project_from_template()
        super(SaleOrderLine, self)._timesheet_service_generation()

    @api.multi
    def generate_project_from_template(self):
        """ Create a project copy of create_from_project_id and will create a
        and relate a analytic account
        """
        self.ensure_one()
        template = self.product_id.create_from_project_id

        # create analytic account
        self.order_id._create_analytic_account(
            prefix=self.product_id.default_code or None)
        account = self.order_id.analytic_account_id

        # copy project from template
        project_name = '%s (%s)' % (
            account.name, self.order_partner_id.ref) \
            if self.order_partner_id.ref else account.name

        project = template.copy({
            'name': project_name,
            'allow_timesheets': self.product_id.service_type == 'timesheet',
            'analytic_account_id': account.id,
        })
        project.write({'sale_line_id': self.id})
        return project
