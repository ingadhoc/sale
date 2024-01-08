from odoo import models, fields, api, _
from odoo.tools import float_compare
from odoo.exceptions import ValidationError
from odoo.osv import expression


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_gathering = fields.Boolean(
        'Is Gathering?',
        states={
            "sale": [("readonly", True)],
            "done": [("readonly", True)]
        }
    )
    gathering_balance = fields.Float(
        compute="_compute_gathering_balance",
        digits='Product Price',
        search='_search_gathering_balance',
        tracking=True,
        help='Balance entre la factura de acopio/anticipo y los retiros de mercaderia que realizo el cliente. Monto positivo es a favor del cliente'
    )
    amount = fields.Float(compute="_compute_amount", help='Monto, sin impuestos, acopiado inicialmente.')
    has_gathering_invoice = fields.Boolean(compute="_compute_has_gathering_invoice")

    @api.depends(
        'is_gathering',
        'order_line.price_unit_with_tax',
        'order_line.qty_invoiced',
        'order_line.is_downpayment',
        'state'
    )
    def _compute_gathering_balance(self):
        orders_gathering = self.filtered(
            lambda order: order.is_gathering and order.state == 'sale' and any(
                order.order_line.filtered('is_downpayment')
            )
        )
        for rec in orders_gathering:
            amount_to_invoice = sum(
                rec.order_line.filtered(lambda x: not x.is_downpayment).mapped(
                    lambda l: l.price_reduce_taxinc * l.qty_to_invoice))
            amount_invoiced = sum(
                rec.order_line.filtered(lambda x: not x.is_downpayment).mapped(
                    lambda l: l.price_reduce_taxinc * l.qty_invoiced))
            downpayment_amount = sum(
                rec.order_line.filtered('is_downpayment').mapped('price_unit_with_tax')
            )
            rec.gathering_balance = downpayment_amount - amount_invoiced - amount_to_invoice
        (self - orders_gathering).gathering_balance = 0

    def _search_gathering_balance(self, operator, value):
        if operator != '>':
            return expression.FALSE_DOMAIN
        orders = self.search([('is_gathering', '=', True)]).filtered(lambda x: x.gathering_balance > 0.0)
        return [('id', 'in', orders.ids)]

    def _get_invoiceable_lines(self, final=False):
        """Return the invoiceable lines for order `self`."""
        invoiceable_lines = super()._get_invoiceable_lines(final=False)
        for rec in self.filtered(lambda x: x.is_gathering and x.gathering_balance > 0.0):
            for line in rec.order_line.filtered('is_downpayment'):
                if final:
                    invoiceable_lines |= line
            invoiceable_lines = invoiceable_lines.filtered(
                lambda line: line.display_type not in ['line_section', 'line_note']
            )
        return invoiceable_lines

    @api.constrains('is_gathering', 'amount_total')
    def _check_gathering_balance(self):
        product_precision_digits = self.env['decimal.precision'].precision_get(
            'Product Price')
        for rec in self.filtered('is_gathering'):
            gathering_lines = rec.order_line.filtered(lambda sol: sol.product_uom_qty > 0 and sol.initial_qty_gathered > 0)
            if gathering_lines and float_compare(rec.gathering_balance, 0.0, precision_digits=product_precision_digits) == -1:
                raise ValidationError(
                    _(
                        "The gathering balance will be negative (%s), you cannot make this modification"
                        " to the order. Order: %s" %
                        (rec.gathering_balance, rec.name)))

    def _action_confirm(self):
        for order in self.filtered('is_gathering'):
            for line in order.order_line:
                line.write({
                    'initial_qty_gathered': line.product_uom_qty,
                    'product_uom_qty': 0
                })
        res = super(SaleOrder, self)._action_confirm()
        return res

    @api.depends('order_line.initial_qty_gathered', 'is_gathering')
    def _compute_amount(self):
        orders_gathering = self.filtered(
            lambda x: x.is_gathering and x.order_line.filtered(lambda x: x.initial_qty_gathered > 0)
        )
        for order in orders_gathering:
            amount_untaxed = 0
            for line in order.order_line.filtered(lambda x: x.initial_qty_gathered > 0):
                tax_results = self.env['account.tax']._compute_taxes(
                    [self.env['account.tax']._convert_to_tax_base_line_dict(
                        line,
                        partner=line.order_id.partner_id,
                        currency=line.order_id.currency_id,
                        product=line.product_id,
                        taxes=line.tax_id,
                        price_unit=line.price_unit,
                        quantity=line.initial_qty_gathered,
                        discount=line.discount,
                        price_subtotal=line.price_subtotal,
                    )])
                totals = list(tax_results['totals'].values())[0]
                amount_untaxed += totals['amount_untaxed']
            order.amount = amount_untaxed
        (self - orders_gathering).amount = 0.0

    @api.constrains('order_line')
    def _check_gathering_order_line(self):
        if (
            self.is_gathering and self.state == 'sale' and not self.invoice_ids
            and self.order_line.filtered(lambda x: x.initial_qty_gathered == 0)
        ):
            raise ValidationError(_("You can't add more products. First create the gathering invoice."))

    @api.depends('is_gathering', 'invoice_ids')
    def _compute_has_gathering_invoice(self):
        orders_gathering = self.filtered('is_gathering')
        for rec in orders_gathering:
            rec.has_gathering_invoice = any(
                invoice._is_downpayment() for invoice in rec.invoice_ids if invoice.state != 'cancel'
            )
        (self - orders_gathering).has_gathering_invoice = False
