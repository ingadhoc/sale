##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, models
from odoo.exceptions import UserError


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def unlink(self):
        confirmed_orders = self.env["sale.order"].search(
            [("pricelist_id", "in", self.ids), ("state", "=", "sale")],
            limit=1,
        )
        if confirmed_orders:
            raise UserError(
                _(
                    "The price list cannot be deleted because it has confirmed sales. "
                    "In these cases, we recommend archiving the list."
                )
            )
        return super().unlink()
