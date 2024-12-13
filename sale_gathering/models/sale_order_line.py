from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    initial_qty_gathered = fields.Float(string='Initial Quantity Gathered', copy=False)

    @api.depends('initial_qty_gathered', 'order_id.is_gathering')
    def _compute_price_unit(self):
        gathering_lines = self.filtered(lambda x: x.order_id.is_gathering and x.initial_qty_gathered > 0)
        super(SaleOrderLine, self - gathering_lines)._compute_price_unit()

    def _prepare_invoice_line(self, **optional_values):
        result = super()._prepare_invoice_line(**optional_values)
        if self.is_downpayment and self._context.get(
                'invoice_gathering', False):
            lines = self.order_id.order_line.filtered(
                lambda x: not x.is_downpayment and x.qty_to_invoice)
            price_subtotal = 0
            for line in lines:
                price_reduce = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                price_subtotal += line.tax_id.compute_all(
                    price_reduce,
                    currency=line.currency_id,
                    quantity=line.qty_to_invoice,
                    product=line.product_id,
                    partner=line.order_id.partner_shipping_id)['total_excluded']
            result['price_unit'] = price_subtotal
            result['quantity'] = -1.0
        return result

    def _convert_to_tax_base_line_dict(self, **kwargs):
        if self.env.context.get('advance_payment') and self.initial_qty_gathered > 0:
            self.ensure_one()
            return self.env['account.tax']._convert_to_tax_base_line_dict(
                self,
                partner=self.order_id.partner_id,
                currency=self.order_id.currency_id,
                product=self.product_id,
                taxes=self.tax_id,
                price_unit=self.price_unit,
                quantity=self.initial_qty_gathered,
                discount=self.discount,
                price_subtotal=self.price_subtotal,
                **kwargs,
            )
        else:
            return super()._convert_to_tax_base_line_dict(**kwargs)

    def write(self, vals):
        if "discount" in vals:
            gathering_lines = self.filtered(
                lambda x: x.order_id.is_gathering and x.order_id.state == 'sale'
            )
            if gathering_lines:
                if gathering_lines.filtered(lambda x: x.initial_qty_gathered > 0):
                    raise UserError(_("You cannot modify the discount of the gathering lines once the sale has been confirmed.\n"))
                if gathering_lines.filtered(lambda x: x.initial_qty_gathered == 0 and (x.qty_invoiced > 0 or x.qty_delivered > 0)):
                    raise UserError(_("It is not possible to add discounts once the product has been invoiced or delivered."))
        return super().write(vals)

    @api.constrains('discount')
    def _check_discount(self):
        for rec in self:
            if rec.order_id.is_gathering and rec.state == 'sale':
                if rec.is_downpayment and rec.discount > 0:
                    raise ValidationError(_("Discounts cannot be added to downpayments."))

                if (
                    not self.env.user._is_superuser()
                    and not self.env.user.has_group('sale_gathering.group_allow_redeemed_product_discounts')
                    and rec.initial_qty_gathered == 0
                    and rec.discount > 0
                ):
                    raise ValidationError(_("Cannot add discounts to redeemed products."))

    def _compute_qty_invoiced(self):
        super()._compute_qty_invoiced()
        for line in self.filtered(lambda x: x.order_id.is_gathering and x.qty_invoiced < 0 and x.is_downpayment):
            line.qty_invoiced = 0

    @api.constrains('product_uom_qty')
    def _check_gathering_invoice(self):
        for rec in self.filtered(
            lambda x: (
                x.order_id.is_gathering
                and x.order_id.state == 'sale'
                and x.product_uom_qty > 0
                and not any(invoice._is_downpayment() for invoice in x.order_id.invoice_ids if invoice.state not in ('cancel', 'draft'))
            )
        ):
            raise ValidationError(
                _("Before adding quantities, you need to create and confirm the gathering invoice.")
            )
