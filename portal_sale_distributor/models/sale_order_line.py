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
            distributor_self = self.sudo().with_context(portal_distributor_line_create=True)
            return super(SaleOrderLine, distributor_self).create(vals_list).with_env(self.env)
        return super().create(vals_list)

    def _get_linked_line(self):
        # Upstream bug: while the order is created the linked line has no id and core's
        # ensure_one() raises. Scoped to the create above, which is the only path that reaches it.
        self.ensure_one()
        if not self.env.context.get("portal_distributor_line_create"):
            return super()._get_linked_line()
        linked = self.linked_line_id or (
            self.linked_virtual_id
            and self.order_id.order_line.filtered(lambda line: line.virtual_id == self.linked_virtual_id)
        )
        if not linked:
            return self.env["sale.order.line"]
        return linked.ensure_one()

    def _compute_purchase_price(self):
        self = self.sudo()
        super()._compute_purchase_price()
