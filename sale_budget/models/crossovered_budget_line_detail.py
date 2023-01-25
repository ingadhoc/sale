##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class CrossoveredBudgetLineDetail(models.Model):
    _name = "crossovered.budget.line.detail"
    _description = "crossovered.budget.line.detail"

    crossovered_budget_line_id = fields.Many2one(
        "crossovered.budget.lines", "Budget Line", ondelete="cascade", index=True, required=True
    )
    product_id = fields.Many2one("product.product", "Product", required=True)
    price_unit = fields.Float("Unit Price", required=True, digits="Product Price")
    discount = fields.Float(
        "Discount (%)",
        digits="Discount",
    )
    price_subtotal = fields.Float(
        compute="_compute_price_subtotal", string="Subtotal", digits="Account"
    )
    product_uom_qty = fields.Float("Quantity", digits="Product UoS", required=True)

    @api.onchange("product_id")
    def onchange_product_id(self):
        for line in self:
            # line.price_unit = line.product_id.price
            line.price_unit = line.product_id.list_price

    @api.depends("price_unit", "product_uom_qty")
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = (
                line.product_uom_qty
                * line.price_unit
                * (1 - (line.discount or 0.0) / 100.0)
            )
