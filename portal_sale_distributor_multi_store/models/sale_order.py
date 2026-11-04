##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_distributor_user(self):
        """User the order belongs to, empty when it is not the order of a portal distributor."""
        self.ensure_one()
        # sudo because a portal user has no read access on res.users
        user = (self.create_uid or self.env.user).sudo()
        if not user.store_id or not user.has_group("portal_sale_distributor.group_portal_backend_distributor"):
            return self.env["res.users"]
        return user

    def _get_distributor_store(self):
        """Store of the distributor the order belongs to, empty for any other order."""
        return self._get_distributor_user().store_id

    def _get_order_type_warehouse(self, allowed_stores):
        """Warehouse the order type sets, empty when sale_order_type is not installed or
        when the distributor could not read its own order in that warehouse."""
        self.ensure_one()
        if "type_id" not in self._fields:
            return self.env["stock.warehouse"]
        # sudo because a portal user has no read access on sale.order.type
        warehouse = self.sudo().type_id.warehouse_id
        if warehouse.store_id and warehouse.store_id not in allowed_stores:
            return self.env["stock.warehouse"]
        return warehouse

    @api.depends("user_id", "company_id")
    def _compute_warehouse_id(self):
        """Standard takes the warehouse from the salesperson of the customer. For a
        distributor it must come from the order type, and from its own store when the type
        sets no warehouse, or it would order from another branch."""
        standard = self.browse()
        warehouses = {}
        allowed_stores = {}
        for order in self:
            user = order._get_distributor_user()
            store = user.store_id
            if not store or (order.state not in ["draft", "sent"] and order.ids):
                standard |= order
                continue
            if user.id not in allowed_stores:
                # same reach as the record rule of stock_multi_store over sale.order
                allowed_stores[user.id] = self.env["res.store"].sudo().search([("id", "child_of", user.store_ids.ids)])
            # the warehouse of the order type is explicit configuration and wins over the
            # store, the same way it does for an order loaded from the backend. We assign it
            # here instead of calling super(), which would read the salesperson.
            type_warehouse = order._get_order_type_warehouse(allowed_stores[user.id])
            if type_warehouse:
                order.warehouse_id = type_warehouse
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
