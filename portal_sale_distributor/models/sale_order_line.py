##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        # sale_margin adds stored precomputed fields restricted to internal users (margin,
        # margin_percent, purchase_price). On create the ORM computes them and then reads them
        # back with the current user, which raises an AccessError for a distributor and keeps the
        # order from being saved. Create as superuser and hand the records back in the user env,
        # so the fields stay hidden for them.
        if self.env.user.has_group("portal_sale_distributor.group_portal_backend_distributor"):
            return super(SaleOrderLine, self.sudo()).create(vals_list).with_env(self.env)
        return super().create(vals_list)

    def _compute_purchase_price(self):
        self = self.sudo()
        super()._compute_purchase_price()
