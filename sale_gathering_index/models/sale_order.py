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
        string="Indexed Gathering Balance",
        compute="_compute_gathering_balance_indexed",
        digits="Product Price",
        help="Balance equivalente del acopio inicial actualizado por el indice de inflacion calculado en este acopio",
    )
    indexed_gathering_amount = fields.Float(
        compute="_compute_indexed_gathering_amount",
        digits="Product Price",
        help="Monto equivalente del acopio inicial actualizado por el indice de inflacion calculado en este acopio",
    )
    indexed_withdrawn_amount = fields.Float(
        compute="_compute_indexed_withdrawn_amount",
    )

    def _get_gathering_confirm_line_vals(self, line):
        vals = super()._get_gathering_confirm_line_vals(line)
        vals["gathering_base_price_unit"] = self._get_current_line_price_unit(line)
        return vals

    def _get_current_line_price_unit(self, line):
        """Unit price the line would get from the current pricelist/list price."""
        price = line.with_company(line.company_id)._get_display_price()
        return line.product_id._get_tax_included_unit_price(
            line.company_id,
            line.order_id.currency_id,
            line.order_id.date_order,
            "sale",
            fiscal_position=line.order_id.fiscal_position_id,
            product_price_unit=price,
            product_currency=line.currency_id,
        )

    def _get_indexed_line_price_unit(self, line):
        """Agreed unit price updated by the list price variation since the order was confirmed.

        The index must only reflect how prices moved after gathering. Comparing the current list
        price against `price_unit` mixed in any discount agreed at gathering time, so an order
        confirmed at a negotiated price showed an index greater than zero right away.
        `gathering_base_price_unit` is the list price snapshot taken on confirmation; lines
        gathered before it existed fall back to `price_unit`, keeping their previous behaviour.
        """
        base_price_unit = line.gathering_base_price_unit or line.price_unit
        if not base_price_unit:
            return line.price_unit
        return line.price_unit * self._get_current_line_price_unit(line) / base_price_unit

    @api.depends(
        "order_line.product_id.list_price",
        "order_line.price_unit",
        "order_line.gathering_base_price_unit",
        "order_line.initial_qty_gathered",
        "order_line.discount",
        "is_gathering",
    )
    def _compute_indexed_gathering_amount(self):
        gathering_orders = self.filtered(
            lambda order: order.is_gathering and any(line.initial_qty_gathered > 0 for line in order.order_line)
        )
        for order in gathering_orders:
            order.indexed_gathering_amount = order._get_gathering_amount(order._get_indexed_line_price_unit)
        (self - gathering_orders).indexed_gathering_amount = 0.0

    @api.depends(
        "is_gathering", "order_line.initial_qty_gathered", "indexed_gathering_amount", "gathering_amount_with_taxes"
    )
    def _compute_index(self):
        gathering_orders = self.filtered(
            lambda order: (
                order.is_gathering
                and any(line.initial_qty_gathered > 0 for line in order.order_line)
                and order.gathering_amount_with_taxes > 0
            )
        )
        for order in gathering_orders:
            order.index = (order.indexed_gathering_amount / order.gathering_amount_with_taxes) - 1
            order.coef = order.index + 1
        (self - gathering_orders).index = 0.0
        (self - gathering_orders).coef = 0.0

    @api.depends("gathering_balance", "index")
    def _compute_gathering_balance_indexed(self):
        for rec in self:
            rec.gathering_balance_indexed = rec.gathering_balance * (1 + rec.index)

    @api.depends("gathering_balance_indexed", "indexed_gathering_amount")
    def _compute_indexed_withdrawn_amount(self):
        orders = self.filtered("is_gathering")
        for rec in orders:
            rec.indexed_withdrawn_amount = rec.indexed_gathering_amount - rec.gathering_balance_indexed
        (self - orders).indexed_withdrawn_amount = 0.0
