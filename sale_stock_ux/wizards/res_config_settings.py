##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    propagate_uom = fields.Boolean(
        "Propagate Unit of Measure",
    )

    def get_values(self):
        res = super().get_values()
        res.update(propagate_uom=self.env["ir.config_parameter"].sudo().get_bool("stock.propagate_uom"))
        return res

    def set_values(self):
        super().set_values()
        self.env["ir.config_parameter"].sudo().set_bool("stock.propagate_uom", self.propagate_uom)
