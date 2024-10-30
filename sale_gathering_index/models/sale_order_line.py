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
        if 'name' in vals:
            if any(
                line.order_id.is_gathering
                and line.order_id.state == 'sale'
                and line.display_type not in ['line_section', 'line_note']
                and not line.is_downpayment
                for line in self
            ):
                raise UserError(_("You can't modify the description."))
        return super().write(vals)

    def _compute_price_unit(self):
        super()._compute_price_unit()
        for rec in self.filtered(lambda x: x.order_id.is_gathering and x.order_id.state == 'sale' and x.initial_qty_gathered == 0):
            if not rec.product_uom or not rec.product_id:
                price_unit = 0.0
            else:
                line = rec.with_company(rec.company_id)
                price = line._get_display_price()
                price_unit = line.product_id._get_tax_included_unit_price_from_price(
                    price,
                    product_taxes=line.product_id.taxes_id.filtered(
                        lambda tax: tax.company_id == line.env.company
                    ),
                    fiscal_position=line.order_id.fiscal_position_id,
                )
            rec.price_unit = price_unit / (rec.order_id.index + 1)

    def _compute_name(self):
        super()._compute_name()
        for line in self.filtered(lambda x: x.order_id.is_gathering and x.order_id.state == 'sale' and x.initial_qty_gathered == 0 and not x.display_type and not x.is_downpayment and x.name):
            line = line.with_company(line.company_id)
            price = line._get_display_price()
            price_unit = line.product_id._get_tax_included_unit_price_from_price(
                price,
                product_taxes=line.product_id.taxes_id.filtered(
                    lambda tax: tax.company_id == line.env.company
                ),
                fiscal_position=line.order_id.fiscal_position_id,
            )
            coefficient = 1 / (line.order_id.index + 1)
            line.name += _(
                "\n(Current price: $%s | Coef: %s%%)"
            ) % (price_unit, round(coefficient, 4))
