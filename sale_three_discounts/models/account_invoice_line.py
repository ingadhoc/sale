##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AccountInvoiceLine(models.Model):

    _inherit = "account.move.line"

    discount1 = fields.Float(
        'Discount 1 (%)',
        digits='Discount',
    )
    discount2 = fields.Float(
        'Discount 2 (%)',
        digits='Discount',
    )
    discount3 = fields.Float(
        'Discount 3 (%)',
        digits='Discount',
    )

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

    @api.onchange('discount1', 'discount2', 'discount3')
    @api.constrains('discount1', 'discount2', 'discount3')
    def _set_discount(self):
        for rec in self.filtered(lambda x: x.move_id.is_sale_document()):
            discount_factor = 1.0
            for discount in [rec.discount1, rec.discount2, rec.discount3]:
                discount_factor = discount_factor * (
                    (100.0 - discount) / 100.0)
            rec.discount = 100.0 - (discount_factor * 100.0)
