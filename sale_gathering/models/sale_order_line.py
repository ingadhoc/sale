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

    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        self.ensure_one()
        if self.initial_qty_gathered > 0 and self.env.context.get("first_gathering_invoice"):
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
        lines_to_check = self.filtered(
            lambda x: x.is_gathering and x.order_id.state == "sale" and x.product_uom_qty > 0
        )
        lines_to_check.order_id._invalidate_invoices_cache()
        for rec in lines_to_check:
            if not any(
                invoice._is_downpayment()
                for invoice in rec.order_id.sudo().invoice_ids
                if invoice.move_type == "out_invoice"
                and invoice.state not in ("cancel", "draft")
                and invoice.payment_state in ("paid", "in_payment")
            ):
                raise ValidationError(
                    _("Before adding quantities, you need to create, confirm and pay the gathering invoice.")
                )

    def _compute_qty_to_deliver(self):
        super()._compute_qty_to_deliver()
        for line in self.filtered(lambda x: x.order_id and x.is_gathering and x.order_id.state == "sale"):
            line.display_qty_widget = True
