##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discount1 = fields.Float('Discount 1 (%)', digits='Discount', compute="_compute_discounts", precompute=True, store=True, readonly=False)
    discount2 = fields.Float('Discount 2 (%)', digits='Discount', compute="_compute_discounts", precompute=True, store=True, readonly=False)
    discount3 = fields.Float('Discount 3 (%)', digits='Discount', compute="_compute_discounts", precompute=True, store=True, readonly=False)
    discount = fields.Float(readonly=True)

    @api.constrains('discount1', 'discount2', 'discount3')
    def check_discount_validity(self):
        for rec in self:
            error = []
            if rec.discount1 > 100:
                error.append('Discount 1')
            if rec.discount2 > 100:
                error.append('Discount 2')
            if rec.discount3 > 100:
                error.append('Discount 3')
            if error:
                raise ValidationError(_(
                    ",".join(error) + " must be less or equal than 100"
                ))

    @api.depends('discount1', 'discount2', 'discount3')
    def _compute_discount(self):
        context = self._context
        for line in self:
            show_discount = line.pricelist_item_id._show_discount()
            if (context.get('recompute_prices') and show_discount) or context.get('onchange_product') or context.get('website_id'):
                super(SaleOrderLine, line)._compute_discount()
            else:
                discount_factor = 1.0
                for discount in [line.discount1, line.discount2, line.discount3]:
                    discount_factor *= (100.0 - discount) / 100.0
                line.discount = 100.0 - (discount_factor * 100.0)

    @api.depends('discount')
    def _compute_discounts(self):
        for line in self:
            context = dict(self._context)
            show_discount = line.pricelist_item_id._show_discount()
            if (context.get('recompute_prices') and show_discount) or context.get('onchange_product') or context.get('website_id'):
                line.discount1 = line.discount
                line.discount2 = 0.0
                line.discount3 = 0.0

    @api.onchange('product_id')
    def _onchange_product(self):
        self.with_context(onchange_product=True)._compute_discounts()

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        res.update({
            'discount1': self.discount1,
            'discount2': self.discount2,
            'discount3': self.discount3
        })
        return res
