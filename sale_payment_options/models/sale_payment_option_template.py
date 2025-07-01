from odoo import fields, models


class SalePaymentOptionTemplate(models.Model):
    _name = "sale.payment.option.template"
    _description = "Sale payment option template"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    payment_option_ids = fields.One2many("sale.payment.option", "payment_option_template_id")
    active = fields.Boolean(default=True)

    def action_open_payment_option_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.payment.option.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_payment_option_template_id": self.id,
            },
        }
