##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):

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
    # TODO do like in invoice line? Make normal field with constraint and
    # oncahnge?
    discount = fields.Float(
        compute='_compute_discounts',
        store=True,
        readonly=True,
        # agregamos states vacio porque lo hereda de la definicion anterior
        states={},
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

    def write(self, vals):
        self.inverse_vals([vals])
        return super().write(vals)

    def inverse_vals(self, vals_list):
        """ No usamos metodo inverse porque en el create odoo termina llamando
        a inverse y unificando los descuentos en la primer linea.
        Además, solo actualizamos con el inverse el primer descuento
        principalmente por compatibilidad con listas que discriminen descuento
        y consideramos que las columnas 2 y 3 son descuentos adicionales y no
        las pisamos
        """
        for vals in vals_list:
            precision = self.env['decimal.precision'].precision_get('Discount')
            if 'discount' in vals \
                    and not {'discount1', 'discount2', 'discount3'} & set(vals.keys()):
                vals.update({
                    'discount1': vals.get('discount'),
                })

    @api.depends('discount1', 'discount2', 'discount3')
    def _compute_discounts(self):
        for rec in self.filtered(lambda x: x.move_type not in ('in_invoice', 'in_refund')):
            discount_factor = 1.0
            for discount in [rec.discount1, rec.discount2, rec.discount3]:
                discount_factor = discount_factor * (
                    (100.0 - discount) / 100.0)
            rec.discount = 100.0 - (discount_factor * 100.0)
