##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleOrderDiscount(models.TransientModel):
    _inherit = 'sale.order.discount'

    discount1 = fields.Float('Discount 1 (%)')
    discount2 = fields.Float('Discount 2 (%)')
    discount3 = fields.Float('Discount 3 (%)')
    discount_percentage = fields.Float(compute="_compute_discount_percentage")

    @api.constrains('discount1', 'discount2', 'discount3')
    def check_discount_validity(self):
        for rec in self:
            error = []
            if rec.discount1 > 1.0:
                error.append('Discount 1')
            if rec.discount2 > 1.0:
                error.append('Discount 2')
            if rec.discount3 > 1.0:
                error.append('Discount 3')
            if error:
                raise ValidationError(_(
                    ",".join(error) + " must be less or equal than 100"
                ))

    @api.depends('discount1', 'discount2', 'discount3')
    def _compute_discount_percentage(self):
        for rec in self:
            discount_factor = 1.0
            for discount in [rec.discount1, rec.discount2, rec.discount3]:
                discount_factor = discount_factor * (1.0 - discount)
            # El siguiente redondeo es porque al ser número flotante tiene muchos dígitos (probar con d1 en 10 y d2 en 10 y ver descripción de producto
            # al agregar descuento global) y el +2 es porque discount_percentage esta entre 0 y 1, por lo tanto para el descuento se multiplica por 100
            rec.discount_percentage = round(1.0 - discount_factor, self.env['decimal.precision'].precision_get('Discount') + 2)

    def action_apply_discount(self):
        super().action_apply_discount()
        self = self.with_company(self.company_id)
        if self.discount_type == 'sol_discount':
            self.sale_order_id.order_line.write(
                {'discount1': self.discount1*100, 'discount2': self.discount2*100, 'discount3': self.discount3*100}
            )
