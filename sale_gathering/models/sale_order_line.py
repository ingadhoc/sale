from odoo import models, fields, api


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
            price_subtotal_incl = lines and sum(lines.mapped(
                lambda l: l.qty_to_invoice * l.price_reduce_taxinc)) or 0.0
            result['price_unit'] = self.tax_id.with_context(
                force_price_include=True).compute_all(
                price_subtotal_incl, currency=self.order_id.currency_id)[
                'total_excluded']
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
