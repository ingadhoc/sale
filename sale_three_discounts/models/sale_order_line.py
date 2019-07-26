##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import odoo.addons.decimal_precision as dp


class SaleOrderLine(models.Model):

    _inherit = "sale.order.line"

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
    # TODO do like in invoice line? Make normal field with constraint and
    # oncahnge?
    discount = fields.Float(
        compute='_compute_discount',
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

    @api.model
    def create(self, vals):
        self.inverse_vals(vals)
        return super().create(vals)

    @api.multi
    def write(self, vals):
        self.inverse_vals(vals)
        return super().write(vals)

    def inverse_vals(self, vals):
        """ No usamos metodo inverse porque en el create odoo termina llamando
        a inverse y unificando los descuentos en la primer linea.
        Además, solo actualizamos con el inverse el primer descuento
        principalmente por compatibilidad con listas que discriminen descuento
        y consideramos que las columnas 2 y 3 son descuentos adicionales y no
        las pisamos
        """
        if 'discount' in vals and not vals.get('discount1')\
                and not vals.get('discount2') and not vals.get('discount3'):
            vals.update({
                'discount1': vals.get('discount'),
            })

    @api.multi
    @api.depends('discount1', 'discount2', 'discount3')
    def _compute_discount(self):
        for rec in self:
            discount_factor = 1.0
            for discount in [rec.discount1, rec.discount2, rec.discount3]:
                discount_factor = discount_factor * (
                    (100.0 - discount) / 100.0)
            rec.discount = 100.0 - (discount_factor * 100.0)

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        res.update({
            'discount1': self.discount1,
            'discount2': self.discount2,
            'discount3': self.discount3
        })
        return res
