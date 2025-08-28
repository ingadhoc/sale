from odoo import api, models


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    @api.model
    def _get_fiscal_position(self, partner, delivery=None):
        if self.env.user.has_group("sales_team_security.group_sale_team_manager"):
            partner = partner.sudo()
        return super()._get_fiscal_position(partner=partner, delivery=delivery)
