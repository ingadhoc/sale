##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    price = fields.Monetary(
        compute="_compute_price",
        help="Price for product specified on the context",
    )
    show_products = fields.Boolean(
        "Show in products",
        default=True,
        help="By selecting it allows you to display the pricelist with the price of that product in the products",
    )

    def _get_context_product(self):
        if product_id := self.env.context.get("pricelist_product_id"):
            return self.env["product.product"].browse(product_id)
        if template_id := self.env.context.get("pricelist_template_id"):
            return self.env["product.template"].browse(template_id)
        return self.env["product.template"]

    def _compute_price(self):
        self = self.sudo()
        product = self._get_context_product()
        if not product:
            self.price = 0.0
            return
        for rec in self:
            contextual_price = product.with_context(pricelist=rec.id)._get_contextual_price()
            rec.sudo().write({"price": contextual_price})

    def action_open_product_pricelist_item(self):
        self.ensure_one()
        product = self._get_context_product()
        if not product:
            raise UserError(_("Open this pricelist from a product to edit its price."))
        is_variant = product._name == "product.product"
        context = {
            "default_pricelist_id": self.id,
            "default_product_tmpl_id": product.product_tmpl_id.id if is_variant else product.id,
            "default_applied_on": "0_product_variant" if is_variant else "1_product",
        }
        if is_variant:
            context["default_product_id"] = product.id
        return {
            "type": "ir.actions.act_window",
            "name": _("Pricelist Rules"),
            "res_model": "product.pricelist.item",
            "view_mode": "list,form",
            "views": [
                (self.env.ref("product.product_pricelist_item_tree_view").id, "list"),
                (self.env.ref("product.product_pricelist_item_form_view").id, "form"),
            ],
            "domain": self._get_applicable_rules_domain(product, fields.Datetime.now()),
            "context": context,
        }

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == "form":
            if (
                self.env.user.has_group("sales_team.group_sale_salesman")
                or self.env.user.has_group("sales_team.group_sale_salesman_all_leads")
            ) and not self.env.user.has_group("sales_team.group_sale_manager"):
                fields = arch.xpath("//form")
                for node in fields:
                    node.set("edit", "false")
        return arch, view

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
