##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    type_id = fields.Many2one(
        tracking=True,
    )

    @api.depends("partner_shipping_id", "partner_id", "company_id", "type_id")
    def _compute_fiscal_position_id(self):
        if self.type_id.fiscal_position_id:
            self.fiscal_position_id = self.type_id.fiscal_position_id
        else:
            return super()._compute_fiscal_position_id()

    @api.model_create_multi
    def create(self, vals):
        res = super().create(vals)
        if res.type_id and self.env.context.get("website_id"):
            res._compute_fiscal_position_id()
        return res

    def _compute_team_id(self):
        res = super()._compute_team_id()
        for order in self.filtered("type_id"):
            order_type = order.type_id
            if order_type.team_id:
                order.team_id = order_type.team_id
        return res

    @api.onchange("type_id")
    def _onchange_team_id(self):
        if self.type_id and self.type_id.team_id:
            self.team_id = self.type_id.team_id

    def _get_protected_fields(self):
        return super()._get_protected_fields() + ["type_id"]
