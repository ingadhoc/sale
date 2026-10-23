##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    only_packagings = fields.Boolean(
        default=False,
        help="Indicates that this product is only used as packaging and does not use units.",
    )
    pricelist_ids = fields.One2many(
        "product.pricelist",
        compute="_compute_pricelist_ids",
        string="Pricelists",
    )

    def _compute_pricelist_ids(self):
        for rec in self:
            rec.pricelist_ids = rec.pricelist_ids.search([("show_products", "=", True)])
            rec.pricelist_ids.with_context(pricelist_template_id=rec.id)._compute_price()

    @api.model
    def get_import_templates(self):
        if self.env.context.get("sale_multi_pricelist_product_template"):
            return [
                {
                    "label": _("Import Template for Products"),
                    "template": "/sale_ux/static/xls/product_template.xlsx",
                }
            ]
        return super().get_import_templates()

    def _get_available_uoms(self):
        if not self:
            # lines without a product (sections, notes, down payment header) get here empty
            return super()._get_available_uoms()
        self.ensure_one()
        res = super()._get_available_uoms()
        if self.only_packagings:
            return self.uom_ids
        return res
