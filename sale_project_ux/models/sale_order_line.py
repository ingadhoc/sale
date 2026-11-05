from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _timesheet_create_project_prepare_values(self):
        """Generate project values"""
        values = super()._timesheet_create_project_prepare_values()
        if self.env["ir.config_parameter"].sudo().get_bool("sale_ux.analytic_account_without_company"):
            values["company_id"] = False
        return values
