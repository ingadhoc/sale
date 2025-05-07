from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _timesheet_create_project_prepare_values(self):
        """Generate project values"""
        if (
            self.env["ir.config_parameter"].sudo().get_param("sale_ux.analytic_account_without_company", "False")
            == "True"
        ):
            return {
                "name": "%s - %s" % (self.order_id.client_order_ref, self.order_id.name)
                if self.order_id.client_order_ref
                else self.order_id.name,
                "partner_id": self.order_id.partner_id.id,
                "sale_line_id": self.id,
                "active": True,
                "company_id": False,
                "allow_billable": True,
                "user_id": self.product_id.project_template_id.user_id.id,
            }
        return super(SaleOrderLine, self)._timesheet_create_project_prepare_values()
