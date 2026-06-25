##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, tools


class ResCompany(models.Model):
    _inherit = "res.company"

    price_checker_pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Price Checker Pricelist",
        domain="['|', ('company_id', '=', False), ('company_id', '=', id)]",
        help="Pricelist used by the public price checker for this company. "
        "If empty, the product's Sales Price (lst_price) is used as a fallback.",
    )

    @tools.ormcache(cache="groups")
    def _price_checker_pricelists_enabled(self):
        pricelist_group = self.env.ref("product.group_product_pricelist", raise_if_not_found=False)
        if not pricelist_group:
            return False
        return pricelist_group in self.env.ref("base.group_user").sudo().implied_ids
