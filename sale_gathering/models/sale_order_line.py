from odoo import api, models


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

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
