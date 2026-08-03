from odoo import models


class ProductCatalogMixin(models.AbstractModel):
    _inherit = "product.catalog.mixin"

    def _get_action_add_from_catalog_extra_context(self):
        ctx = super()._get_action_add_from_catalog_extra_context()
        if self.env.user.has_group("portal_sale_distributor.group_portal_backend_distributor_stock"):
            ctx["display_stock"] = True
        return ctx
