##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    price_checker_pricelist_id = fields.Many2one(
        related="company_id.price_checker_pricelist_id",
        readonly=False,
    )

    def action_open_price_checker(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/price-checker/{self.company_id.id}",
            "target": "new",
        }
