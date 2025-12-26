from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_preview_sale_order(self):
        """Override to check print exceptions before website_sale processes the action.
        This prevents the KeyError when trying to access action['url'] on a popup action
        that doesn't have a 'url' key.
        """
        self.ensure_one()
        if self.detect_print_exceptions():
            return self.with_context(print_exceptions=True)._popup_exceptions()
        return super().action_preview_sale_order()
