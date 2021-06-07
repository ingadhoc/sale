from odoo import models, fields, api, _
from odoo.tools import float_compare
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    is_gathering = fields.Boolean('Is Gathering?')

    gathering_balance = fields.Float(
        compute="_compute_gathering_balance",
        digits='Product Price',
    )

    @api.depends(
        'is_gathering',
        'order_line.price_unit_with_tax',
        'order_line.qty_invoiced',
        'order_line.is_downpayment',
    )
    def _compute_gathering_balance(self):
        self.gathering_balance = 0.0
        for rec in self.filtered('is_gathering'):
            amount_to_invoice = sum(
                rec.order_line.filtered(lambda x: not x.is_downpayment).mapped(
                    lambda l: l.price_reduce_taxinc * l.qty_to_invoice))
            amount_invoiced = sum(
                rec.order_line.filtered(lambda x: not x.is_downpayment).mapped(
                    lambda l: l.price_reduce_taxinc * l.qty_invoiced))
            rec.gathering_balance = sum(
                rec.order_line.filtered('is_downpayment').mapped(
                    'price_unit_with_tax')) - amount_invoiced - amount_to_invoice

    def _get_invoiceable_lines(self, final=False):
        """Return the invoiceable lines for order `self`."""
        invoiceable_lines = super()._get_invoiceable_lines(final=False)
        if self.is_gathering and self.gathering_balance > 0.0:
            for line in self.order_line.filtered('is_downpayment'):
                if final:
                    invoiceable_lines |= line
        return invoiceable_lines

    @api.constrains('is_gathering', 'amount_total')
    def _check_gathering_balance(self):
        product_precision_digits = self.env['decimal.precision'].precision_get(
            'Product Price')
        for rec in self.filtered('is_gathering'):
            if float_compare(rec.gathering_balance, 0.0, precision_digits=product_precision_digits) == -1:
                raise ValidationError(
                    _(
                        "The gathering balance will be negative (%s), you cannot make this modification"
                        " to the order. Order: %s" %
                        (rec.gathering_balance, rec.name)))
