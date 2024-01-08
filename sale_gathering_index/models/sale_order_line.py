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
        if (
            self.order_id.is_gathering
            and self.order_id.state == 'sale'
            and 'product_uom_qty' in vals
            and vals['product_uom_qty'] > self.product_uom_qty
            and 'initial_qty_gathered' not in vals
            and self.initial_qty_gathered == 0
        ):
            raise UserError(_("You can't modify the quantity of an added product. Please add a new line."))
        return super(SaleOrderLine, self).write(vals)

    def _compute_price_unit(self):
        super()._compute_price_unit()
        for rec in self.filtered(lambda x: x.order_id.is_gathering and x.order_id.state == 'sale' and x.initial_qty_gathered == 0):
            rec.price_unit = rec.price_unit / (rec.order_id.index + 1)

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
            line.name += "\n($%s)\n(%s%%)" % (line_price, round(line.order_id.index*100, 2))
