from odoo import models, fields, api, _
from odoo.tools import float_compare
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_gathering = fields.Boolean('Is Gathering?')
    gathering_balance = fields.Float(
        compute="_compute_gathering_balance",
        digits='Product Price',
        store=True,
        tracking=True,
        help='Balance entre la factura de acopio/anticipo y los retiros de mercaderia que realizo el cliente. Monto positivo es a favor del cliente'
    )
    gathering_amount = fields.Float(compute="_compute_gathering_amount")
    gathering_amount_with_taxes = fields.Float(compute="_compute_gathering_amount", help='Monto acopiado inicialmente.')
    has_gathering_invoice = fields.Boolean(compute="_compute_has_gathering_invoice")
    withdrawn_amount = fields.Float(compute="_compute_withdrawn_amount", help='El monto retirado (o solicitado) se calcula en base a la columna cantidad de las lineas de ventas, no necesariamente tienen que estar entregadas/facturadas esas lineas de venta.')

    @api.depends(
        'is_gathering',
        'order_line.price_unit_with_tax',
        'order_line.qty_invoiced',
        'order_line.qty_to_invoice',
        'order_line.is_downpayment',
        'order_line.qty_to_deliver',
        'order_line.quantity_returned',
        'state'
    )
    def _compute_gathering_balance(self):
        orders_gathering = self.filtered(
            lambda order: order.is_gathering and order.state == 'sale' and any(
                order.order_line.filtered('is_downpayment')
            )
        )

        for order in orders_gathering:
            total_downpayment_amount = sum(
                line.price_unit_with_tax
                for line in order.order_line.filtered('is_downpayment')
            )
            order_lines = order.order_line.filtered(lambda x: not x.is_downpayment)
            tax_totals = order.env['account.tax']._compute_taxes([
                {
                    **line._convert_to_tax_base_line_dict(),
                    'quantity': (
                        line.qty_to_invoice + line.qty_invoiced + line.qty_to_deliver - line.quantity_returned
                        if line.product_id.invoice_policy == 'delivery' else
                        line.qty_to_invoice + line.qty_invoiced
                    )
                }
                for line in order_lines
            ])
            totals = list(tax_totals['totals'].values())[0]
            total_amount_to_invoice_invoiced = totals['amount_untaxed'] + totals['amount_tax']  # total amount qty to invoice + qty invoiced
            order.gathering_balance = total_downpayment_amount - total_amount_to_invoice_invoiced

        (self - orders_gathering).gathering_balance = 0

    def _get_invoiceable_lines(self, final=False):
        """Return the invoiceable lines for order `self`."""
        invoiceable_lines = super()._get_invoiceable_lines(final=final)
        product_precision_digits = self.env['decimal.precision'].precision_get('Product Price')
        for rec in self.filtered(lambda x: x.is_gathering and float_compare(x.gathering_balance, 0.0, precision_digits=product_precision_digits) >= 0):
            for line in rec.order_line.filtered('is_downpayment'):
                if final:
                    invoiceable_lines |= line
            invoiceable_lines = invoiceable_lines.filtered(lambda line: line.display_type not in ['line_section', 'line_note'])
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

    def _action_confirm(self):
        for line in self.filtered(lambda x: x.is_gathering and x.order_line.filtered(lambda x: x.product_uom_qty > 0)).mapped('order_line'):
            line.write({
                'initial_qty_gathered': line.product_uom_qty,
                'product_uom_qty': 0
            })
        return super(SaleOrder, self)._action_confirm()

    @api.depends('order_line.initial_qty_gathered', 'is_gathering')
    def _compute_gathering_amount(self):
        orders_gathering = self.filtered(
            lambda x: x.is_gathering and x.order_line.filtered(lambda x: x.initial_qty_gathered > 0)
        )
        for order in orders_gathering:
            price_subtotal = 0
            price_subtotal_with_taxes = 0
            for line in order.order_line.filtered(lambda x: x.initial_qty_gathered > 0):
                price_reduce = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                subtotal = line.tax_id.compute_all(
                                price_reduce,
                                currency=line.currency_id,
                                quantity=line.initial_qty_gathered,
                                product=line.product_id,
                                partner=line.order_id.partner_shipping_id)
                price_subtotal += subtotal['total_excluded']
                price_subtotal_with_taxes += subtotal['total_included']
            order.gathering_amount = price_subtotal
            order.gathering_amount_with_taxes = price_subtotal_with_taxes
        (self - orders_gathering).gathering_amount = 0.0
        (self - orders_gathering).gathering_amount_with_taxes = 0.0

    @api.depends('is_gathering', 'invoice_ids', 'invoice_ids.state')
    def _compute_has_gathering_invoice(self):
        orders_gathering = self.filtered('is_gathering')
        for rec in orders_gathering:
            rec.has_gathering_invoice = any(
                invoice._is_downpayment() for invoice in rec.invoice_ids if invoice.state != 'cancel'
            )
        (self - orders_gathering).has_gathering_invoice = False

    def action_lock(self):
        super(SaleOrder, self - self.filtered('is_gathering')).action_lock()

    @api.depends('gathering_balance', 'gathering_amount_with_taxes')
    def _compute_withdrawn_amount(self):
        orders = self.filtered(lambda x: x.gathering_balance > 0)
        for rec in orders:
            rec.withdrawn_amount = rec.gathering_amount_with_taxes - rec.gathering_balance
        (self - orders).withdrawn_amount = 0.0

    def write(self, values):
        protected_fields = self._get_protected_fields()
        if any(state in ['sale', 'done'] for state in self.mapped('state')) and any(f in values.keys() for f in protected_fields):
            protected_fields_modified = list(set(protected_fields) & set(values.keys()))
            fields = self.env['ir.model.fields'].sudo().search([
                ('name', 'in', protected_fields_modified), ('model', '=', self._name)
            ])
            if fields:
                raise UserError(
                    _('It is forbidden to modify the following fields in a confirmed order:\n%s')
                    % '\n'.join(fields.mapped('field_description'))
                )
        return super().write(values)

    def _get_protected_fields(self):
        return ['is_gathering']
