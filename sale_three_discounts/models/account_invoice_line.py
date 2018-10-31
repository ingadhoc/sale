##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api
import odoo.addons.decimal_precision as dp


class account_invoice_line(models.Model):

    _inherit = "account.invoice.line"

    discount1 = fields.Float(
        'Discount 1 (%)',
        digits=dp.get_precision('Discount'),
    )
    discount2 = fields.Float(
        'Discount 2 (%)',
        digits=dp.get_precision('Discount'),
    )
    discount3 = fields.Float(
        'Discount 3 (%)',
        digits=dp.get_precision('Discount'),
    )
    discount_readonly = fields.Float(
        related="discount",
    )

    @api.onchange('discount1', 'discount2', 'discount3')
    @api.constrains('discount1', 'discount2', 'discount3')
    def _set_discount(self):
        for rec in self:
            discount_factor = 1.0
            for discount in [rec.discount1, rec.discount2, rec.discount3]:
                discount_factor = discount_factor * (
                    (100.0 - discount) / 100.0)
            rec.discount = 100.0 - (discount_factor * 100.0)
