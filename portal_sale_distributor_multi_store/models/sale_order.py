##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_distributor_store(self):
        """Store of the distributor the order belongs to, empty for any other order."""
        self.ensure_one()
        # sudo because a portal user has no read access on res.users
        user = self.create_uid.sudo() or self.env.user
        if not user.store_id or not user.has_group("portal_sale_distributor.group_portal_backend_distributor"):
            return self.env["res.store"]
        return user.store_id

    @api.depends("user_id", "company_id")
    def _compute_warehouse_id(self):
        """Standard takes the warehouse from the salesperson of the customer. For a
        distributor it must come from its own store, or it would order from another branch."""
        standard = self.browse()
        warehouses = {}
        for order in self:
            store = order._get_distributor_store()
            if not store or (order.state not in ["draft", "sent"] and order.ids):
                standard |= order
                continue
            key = (store.id, order.company_id.id)
            if key not in warehouses:
                company_domain = [("company_id", "=", order.company_id.id)]
                # the own warehouse wins over the ones of the child stores, whatever their sequence
                warehouses[key] = self.env["stock.warehouse"].search(
                    [("store_id", "=", store.id)] + company_domain, limit=1
                ) or self.env["stock.warehouse"].search([("store_id", "child_of", store.ids)] + company_domain, limit=1)
            if warehouses[key]:
                order.warehouse_id = warehouses[key]
            else:
                standard |= order
        # standard reads the salesperson, something a portal user is not allowed to do,
        # so we only fall back for the orders we could not resolve from the store
        if standard:
            super(SaleOrder, standard)._compute_warehouse_id()
