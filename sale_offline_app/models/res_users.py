from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = "res.users"

    # Only a screen lock for the offline app: it travels and is stored on the device as is.
    offline_app_pin = fields.Char(
        string="Offline App PIN",
        copy=False,
        groups="base.group_erp_manager",
        help="4 to 6 digits asked by the offline sales app every time it is opened.",
    )

    @api.constrains("offline_app_pin")
    def _check_offline_app_pin(self):
        for user in self.sudo():
            pin = user.offline_app_pin
            if pin and not (pin.isdigit() and 4 <= len(pin) <= 6):
                raise ValidationError(self.env._("The offline app PIN must have 4 to 6 digits."))

    def action_set_offline_app_pin(self):
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Offline App PIN"),
            "res_model": "res.users.offline.pin.wizard",
            "view_mode": "form",
            "target": "new",
        }
