##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _load_pos_data_domain(self, data):
        # an archived current user (e.g. the superuser) must still be loaded
        return super()._load_pos_data_domain(data) + [("active", "in", [True, False])]
