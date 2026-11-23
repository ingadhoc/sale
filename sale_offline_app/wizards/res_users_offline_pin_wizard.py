from odoo import fields, models
from odoo.exceptions import UserError


class ResUsersOfflinePinWizard(models.TransientModel):
    """Lets users set their own offline app PIN without reading anyone else's."""

    _name = "res.users.offline.pin.wizard"
    _description = "Set Offline App PIN"

    pin = fields.Char(string="New PIN")
    pin_confirm = fields.Char(string="Repeat PIN")

    def action_save(self):
        self.ensure_one()
        if (self.pin or "") != (self.pin_confirm or ""):
            raise UserError(self.env._("The two PINs do not match."))
        self.env.user.sudo().offline_app_pin = self.pin or False
        return {"type": "ir.actions.act_window_close"}
