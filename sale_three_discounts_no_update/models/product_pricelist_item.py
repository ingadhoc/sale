from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools import config


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    @api.constrains("compute_price")
    def _check_compute_price_not_percentage(self):
        # Skip during demo data loading (install_mode) and test runs (test_enable):
        # Odoo core demo and demo_full tests create "percentage" pricelist rules.
        if self.env.context.get("install_mode") or config["test_enable"]:
            return
        if any(item.compute_price == "percentage" for item in self):
            raise ValidationError(
                self.env._(
                    "Discount rules are not allowed with module sale_three_discounts_no_update. "
                    'Please use "Formula" instead.'
                )
            )
