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

    @api.depends('order_line.product_id.list_price')
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
                price_reduce = line_price * (1 - (line.discount or 0.0) / 100.0)
                price_subtotal = line.tax_id.compute_all(
                                price_reduce,
                                currency=line.currency_id,
                                quantity=line.initial_qty_gathered,
                                product=line.product_id,
                                partner=line.order_id.partner_shipping_id)['total_excluded']
                indexed_gathering_amount += price_subtotal
            order.indexed_gathering_amount = indexed_gathering_amount
        (self - gathering_orders).indexed_gathering_amount = 0.0

    @api.depends('is_gathering', 'order_line.initial_qty_gathered', 'indexed_gathering_amount', 'gathering_amount')
    def _compute_index(self):
        gathering_orders = self.filtered(
            lambda x: x.is_gathering and x.order_line.filtered(lambda x: x.initial_qty_gathered > 0) and x.gathering_amount > 0
        )
        for order in gathering_orders:
            order.index = (order.indexed_gathering_amount / order.gathering_amount) - 1
        (self - gathering_orders).index = 0.0

    @api.depends('gathering_balance', 'index')
    def _compute_gathering_balance_indexed(self):
        self.gathering_balance_indexed = self.gathering_balance * (1 + self.index)
