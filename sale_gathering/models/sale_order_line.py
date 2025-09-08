from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    initial_qty_gathered = fields.Float(string="Initial Quantity Gathered", copy=False)
    is_gathering = fields.Boolean(related="order_id.is_gathering")

    @api.depends("initial_qty_gathered", "is_gathering")
    def _compute_price_unit(self):
        gathering_lines = self.filtered(lambda x: x.is_gathering and x.initial_qty_gathered > 0)
        super(SaleOrderLine, self - gathering_lines)._compute_price_unit()

    def _prepare_invoice_line(self, **optional_values):
        result = super()._prepare_invoice_line(**optional_values)
        if self.is_downpayment and self._context.get("invoice_gathering", False):
            lines = self.order_id.order_line.filtered(lambda x: not x.is_downpayment and x.qty_to_invoice)
            price_subtotal = 0
            for line in lines:
                price_subtotal += line._get_tax_included_amount(line.qty_to_invoice)
            result["price_unit"] = price_subtotal
            result["quantity"] = -1.0
        return result

    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        if self.env.context.get("advance_payment") and self.initial_qty_gathered > 0:
            self.ensure_one()
            kwargs["quantity"] = self.initial_qty_gathered
            return super()._prepare_base_line_for_taxes_computation(**kwargs)
        else:
            return super()._prepare_base_line_for_taxes_computation(**kwargs)

    def write(self, vals):
        if "discount" in vals:
            gathering_lines = self.filtered(lambda x: x.is_gathering and x.order_id.state == "sale")
            if gathering_lines:
                if gathering_lines.filtered(lambda x: x.initial_qty_gathered > 0):
                    raise UserError(
                        _("You cannot modify the discount of the gathering lines once the sale has been confirmed.\n")
                    )
                if gathering_lines.filtered(
                    lambda x: x.initial_qty_gathered == 0 and (x.qty_invoiced > 0 or x.qty_delivered > 0)
                ):
                    raise UserError(
                        _("It is not possible to add discounts once the product has been invoiced or delivered.")
                    )
        return super().write(vals)

    @api.constrains("discount")
    def _check_discount(self):
        for rec in self:
            if rec.is_gathering and rec.state == "sale":
                if rec.is_downpayment and rec.discount > 0:
                    raise ValidationError(_("Discounts cannot be added to downpayments."))

                if (
                    not self.env.user._is_superuser()
                    and not self.env.user.has_group("sale_gathering.group_allow_redeemed_product_discounts")
                    and rec.initial_qty_gathered == 0
                    and rec.discount > 0
                ):
                    raise ValidationError(_("Cannot add discounts to redeemed products."))

    def _compute_qty_invoiced(self):
        super()._compute_qty_invoiced()
        for line in self.filtered(lambda x: x.is_gathering and x.qty_invoiced < 0 and x.is_downpayment):
            line.qty_invoiced = 0

    @api.constrains("product_uom_qty")
    def _check_gathering_invoice(self):
        for rec in self.filtered(
            lambda x: (
                x.is_gathering
                and x.order_id.state == "sale"
                and x.product_uom_qty > 0
                and not any(
                    invoice._is_downpayment()
                    for invoice in x.order_id.invoice_ids
                    if invoice.state not in ("cancel", "draft")
                )
            )
        ):
            raise ValidationError(_("Before adding quantities, you need to create and confirm the gathering invoice."))

    def _compute_qty_to_deliver(self):
        super()._compute_qty_to_deliver()
        for line in self.filtered(lambda x: x.order_id and x.is_gathering and x.order_id.state == "sale"):
            line.display_qty_widget = True

    def _get_tax_included_amount(self, quantity, price=None):
        "Helper method to compute tax included amount for a given quantity"
        self.ensure_one()
        base_line = self._prepare_base_line_for_taxes_computation()
        base_line["quantity"] = quantity
        if price is not None:
            base_line["price_unit"] = price
        self.env["account.tax"]._add_tax_details_in_base_line(base_line, self.company_id)
        return base_line["tax_details"]["raw_total_included_currency"]
