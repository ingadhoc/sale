##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _load_pos_data(self, data):
        return super(ResUsers, self.with_context(active_test=False))._load_pos_data(data)
