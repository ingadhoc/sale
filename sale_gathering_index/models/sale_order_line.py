from odoo import models, api, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.constrains('product_id')
    def _check_existing_gathering_products(self):
        for rec in self.filtered(lambda x: x.order_id.is_gathering and x.order_id.state == 'sale'):
            existing_product_ids = self.env['sale.order.line'].search([
                ('order_id', '=', rec.order_id.id),
                ('initial_qty_gathered', '>', 0)
            ]).mapped('product_template_id.id')
            if rec.product_template_id.id in existing_product_ids:
                raise UserError(_("You can't add an already gathered product more than once. Please modify the quantity of the existing line."))

    def write(self, vals):
        if 'product_uom_qty' in vals and 'initial_qty_gathered' not in vals:
            if any(
                line.order_id.is_gathering
                and line.order_id.state == 'sale'
                and vals['product_uom_qty'] > line.product_uom_qty
                and line.initial_qty_gathered == 0 for line in self
            ):
                raise UserError(_("You can't modify the quantity of an added product. Please add a new line."))
        return super(SaleOrderLine, self).write(vals)

    def _compute_price_unit(self):
        super()._compute_price_unit()
        for rec in self.filtered(lambda x: x.order_id.is_gathering and x.order_id.state == 'sale' and x.initial_qty_gathered == 0):
            """
            Evaluamos si es NewId porque al agregar una nueva línea a la orden de venta (sin guardar) el index
            lo toma como 0 al no poner _origin ya que en esa order new aún no ha sido calculado el índice.
            Utilizamos el origin de forma segura ya que filtramos las órdenes de venta que están en estado 'sale'
            por lo tanto ya cuando busque el origin va a existir en la base de datos y no va a haber error.
            Otra forma que funcionó es haciendo depends de order_id.index pero solamente entraba a compute_name
            y para que ingrese a este método (no entiendo por qué no lo hacía) tenía que poner el price_unit
            como recursive=True, pero este último approach ingresaba varias veces a computar y tiene menor performance.
            """
            if isinstance(rec.order_id.id, models.NewId):
                index = rec.order_id._origin.index
            else:
                index = rec.order_id.index
            rec.price_unit = rec.price_unit / (index + 1)

    def _compute_name(self):
        super()._compute_name()
        for line in self.filtered(lambda x: x.order_id.is_gathering and x.order_id.state == 'sale' and x.initial_qty_gathered == 0 and not x.display_type and not x.is_downpayment and x.name):
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
            # misma nota que en método _compute_price_unit
            if isinstance(line.order_id.id, models.NewId):
                index = line.order_id._origin.index
            else:
                index = line.order_id.index
            line.name += "\n($%s)\n(%s%%)" % (line_price, round(index*100, 2))
