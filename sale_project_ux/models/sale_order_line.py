from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _timesheet_create_project_prepare_values(self):
        """Generate project values"""
        values = super()._timesheet_create_project_prepare_values()
        if self.env["ir.config_parameter"].sudo().get_bool("sale_ux.analytic_account_without_company"):
            values["company_id"] = False
            # An account with company cannot be shared with a project without company
            AnalyticAccount = self.env["account.analytic.account"]
            if AnalyticAccount.browse(values.get("account_id")).company_id:
                values["account_id"] = AnalyticAccount.create(self.order_id._prepare_analytic_account_data()).id
        return values
