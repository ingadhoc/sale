from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    index = fields.Float(
        compute="_compute_index",
        help="Variación de precio promedio de los productos acopiados. El mismo se calcula ponderando por cantidades acopiadas.",
    )
    coef = fields.Float(
        compute="_compute_index",
        digits=(12, 4),
        help="Coeficiente inverso que se utiliza para estimar el precio de un producto canjeado a la fecha de confirmación del acopio. Para calcular el precio se toma el precio actual del producto y se lo divide por este coeficiente.",
    )
    gathering_balance_indexed = fields.Float(
        compute="_compute_gathering_balance_indexed",
        digits="Product Price",
        help="Balance equivalente del acopio inicial actualizado por el indice de inflacion calculado en este acopio",
    )
    indexed_gathering_amount = fields.Float(
        compute="_compute_indexed_gathering_amount",
        digits="Product Price",
        help="Monto equivalente del acopio inicial actualizado por el indice de inflacion calculado en este acopio",
    )

    @api.depends("order_line.product_id.list_price")
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
                    "sale",
                    fiscal_position=line.order_id.fiscal_position_id,
                    product_price_unit=price,
                    product_currency=line.currency_id,
                )
                price_reduce = line_price * (1 - (line.discount or 0.0) / 100.0)
                price_subtotal = line.tax_id.compute_all(
                    price_reduce,
                    currency=line.currency_id,
                    quantity=line.initial_qty_gathered,
                    product=line.product_id,
                    partner=line.order_id.partner_shipping_id,
                )["total_included"]
                indexed_gathering_amount += price_subtotal
            order.indexed_gathering_amount = indexed_gathering_amount
        (self - gathering_orders).indexed_gathering_amount = 0.0

    @api.depends(
        "is_gathering", "order_line.initial_qty_gathered", "indexed_gathering_amount", "gathering_amount_with_taxes"
    )
    def _compute_index(self):
        gathering_orders = self.filtered(
            lambda x: x.is_gathering
            and x.order_line.filtered(lambda x: x.initial_qty_gathered > 0)
            and x.gathering_amount_with_taxes > 0
        )
        for order in gathering_orders:
            order.index = (order.indexed_gathering_amount / order.gathering_amount_with_taxes) - 1
            order.coef = order.index + 1
        (self - gathering_orders).index = 0.0
        (self - gathering_orders).coef = 0.0

    @api.depends("gathering_balance", "index")
    def _compute_gathering_balance_indexed(self):
        self.gathering_balance_indexed = self.gathering_balance * (1 + self.index)

    @api.depends("gathering_balance_indexed", "indexed_gathering_amount")
    def _compute_withdrawn_amount(self):
        # the sale_gathering method is overridden to focus on the indexed amount
        orders = self.filtered(lambda x: x.gathering_balance_indexed > 0)
        for rec in orders:
            rec.withdrawn_amount = rec.indexed_gathering_amount - rec.gathering_balance_indexed
        (self - orders).withdrawn_amount = 0.0
