from odoo import api, models


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'


    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        price_unit = self.price_unit
        res = super().product_uom_change()
        if self.order_id.is_gathering:
            self.price_unit = price_unit
        return res

    def _prepare_invoice_line(self):
        result = super()._prepare_invoice_line()
        # if self.is_downpayment and self._context.get('invoice_gathering', False):
        #     invoices = self.env['account.move'].browse(self._context.get('invoice_ids'))
        #     result['price_unit'] = sum(invoices.mapped('amount_untaxed'))
        #     result['quantity'] = 1.0
        if self.is_downpayment and self._context.get('invoice_gathering', False):
            lines = self.order_id.order_line.filtered(lambda x: not x.is_downpayment and x.qty_to_invoice)
            result['price_unit'] = lines and sum(lines.mapped('untaxed_amount_to_invoice')) or 0.0
            result['quantity'] = -1.0
        return result

