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
        if self.is_downpayment and self._context.get('invoice_ids', False):
            invoices = self.env['account.move'].browse(self._context.get('invoice_ids'))
            result['price_unit'] = sum(invoices.mapped('amount_untaxed'))
        return result
