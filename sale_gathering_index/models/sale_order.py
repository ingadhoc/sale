from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    index = fields.Float('Index', compute="_compute_index")
    gathering_balance_indexed = fields.Float(
        compute="_compute_gathering_balance_indexed",
        digits='Product Price',
        help='Balance equivalente del acopio inicial actualizado por el indice de inflacion calculado en este acopio'
    )
    indexed_gathering_amount = fields.Float(
        compute="_compute_indexed_gathering_amount",
        digits='Product Price',
        help='Monto equivalente del acopio inicial actualizado por el indice de inflacion calculado en este acopio'
    )

    @api.depends('order_line.product_id.lst_price')
    def _compute_indexed_gathering_amount(self):
        gathering_orders = self.filtered(
            lambda x: x.is_gathering and x.order_line.filtered(lambda x: x.initial_qty_gathered > 0)
        )
        for order in gathering_orders:
            indexed_gathering_amount = 0.0
            for line in order.order_line.filtered(lambda x: x.initial_qty_gathered > 0):
                price = line.with_company(line.company_id)._get_display_price()
                line_price = line.product_id._get_tax_included_unit_price(
                    line.company_id,
                    line.order_id.currency_id,
                    line.order_id.date_order,
                    'sale',
                    fiscal_position=line.order_id.fiscal_position_id,
                    product_price_unit=price,
                    product_currency=line.currency_id
                )
                tax_results = self.env['account.tax']._compute_taxes(
                    [self.env['account.tax']._convert_to_tax_base_line_dict(
                        line,
                        partner=line.order_id.partner_id,
                        currency=line.order_id.currency_id,
                        product=line.product_id,
                        taxes=line.tax_id,
                        price_unit=max(line_price, line.price_unit),
                        quantity=line.initial_qty_gathered,
                        discount=line.discount,
                        price_subtotal=line.price_subtotal,
                    )])
                totals = list(tax_results['totals'].values())[0]
                indexed_gathering_amount += totals['amount_untaxed']
            order.indexed_gathering_amount = indexed_gathering_amount
        (self - gathering_orders).indexed_gathering_amount = 0.0

    @api.depends('is_gathering', 'order_line.initial_qty_gathered', 'indexed_gathering_amount', 'amount')
    def _compute_index(self):
        gathering_orders = self.filtered(
            lambda x: x.is_gathering and x.order_line.filtered(lambda x: x.initial_qty_gathered > 0)
        )
        for order in gathering_orders:
            order.index = (order.indexed_gathering_amount / order.amount) - 1
        (self - gathering_orders).index = 0.0

    @api.depends('gathering_balance', 'index')
    def _compute_gathering_balance_indexed(self):
        self.gathering_balance_indexed = self.gathering_balance * (1 + self.index)
