from odoo import models


class ProductCatalogMixin(models.AbstractModel):
    _inherit = "product.catalog.mixin"

    def _get_action_add_from_catalog_extra_context(self):
        display_stock = (
            True if self.env.user.has_group("portal_sale_distributor.group_portal_backend_distributor_stock") else False
        )
        return {
            **super()._get_action_add_from_catalog_extra_context(),
            "display_stock": display_stock,
        }
