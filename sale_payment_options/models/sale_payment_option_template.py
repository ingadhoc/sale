from odoo import api, fields, models


class SalePaymentOptionTemplate(models.Model):
    _name = "sale.payment.option.template"
    _description = "Sale payment option template"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    payment_option_ids = fields.One2many("sale.payment.option", "payment_option_template_id")
    active = fields.Boolean(default=True)

    @api.constrains("payment_option_ids")
    def _check_payment_options_percentages(self):
        """Also on the template, so deleting part of an option does not leave the rest under 100%."""
        for template in self:
            template.payment_option_ids._check_payment_options_percentages()
