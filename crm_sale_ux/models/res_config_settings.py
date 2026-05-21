# © 2026 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    crm_auto_won_on_sale_confirm = fields.Boolean(
        string="Mark opportunity as won on sales order confirmation",
        config_parameter="crm_sale_ux.auto_won_on_sale_confirm",
        help="When enabled, confirming a quotation linked to an opportunity marks that opportunity as Won.",
    )
