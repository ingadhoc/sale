from odoo import models, fields


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    is_gathering = fields.Boolean('Is Gathering?')

    amount_gathering = fields.Float(compute="_compute_amount_gathering")

    def _compute_amount_gathering(self):
        for rec in self:
            # amount_lines = sum(rec.order_line.filtered(
            #     lambda x: not x.is_downpayment).mapped(
            #     lambda x: x.qty_invoiced * x.price_unit))
            amount_to_invoice = sum(rec.order_line.filtered(
                lambda x: not x.is_downpayment).mapped('untaxed_amount_to_invoice'))
            amount_invoiced = sum(rec.order_line.filtered(
                lambda x: not x.is_downpayment).mapped('untaxed_amount_invoiced'))
            rec.amount_gathering = sum(
                rec.order_line.filtered('is_downpayment').mapped('price_unit')) - amount_invoiced - amount_to_invoice


    def _get_invoiceable_lines(self, final=False):
        """Return the invoiceable lines for order `self`."""
        invoiceable_lines = super()._get_invoiceable_lines(final=False)
        if self.is_gathering and self.amount_gathering > 0.0:
            for line in self.order_line.filtered('is_downpayment'):
                if final:
                    invoiceable_lines |= line
        return invoiceable_lines

