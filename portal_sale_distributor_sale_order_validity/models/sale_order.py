##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def update_date_prices_and_validity(self):
        # Public method: check the access with the real user before escalating, the sudo would
        # otherwise let a distributor rewrite somebody else's order over rpc.
        if self.env.user.has_group("portal_sale_distributor.group_portal_backend_distributor"):
            self.check_access("write")
            self = self.sudo()
        return super().update_date_prices_and_validity()
