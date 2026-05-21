# © 2026 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.tools import str2bool


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        res = super().action_confirm()

        enabled = str2bool(
            self.env["ir.config_parameter"].sudo().get_param("crm_sale_ux.auto_won_on_sale_confirm", "False"),
            False,
        )
        if not enabled:
            return res

        opportunities = self.mapped("opportunity_id").filtered(
            lambda lead: lead.type == "opportunity" and not lead.stage_id.is_won
        )
        if opportunities:
            opportunities.action_set_won()

        return res
