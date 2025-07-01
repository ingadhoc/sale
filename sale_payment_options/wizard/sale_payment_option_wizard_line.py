from odoo import api, fields, models
from odoo.tools import float_round


class SalePaymentOptionWizardLine(models.TransientModel):
    _name = "sale.payment.option.wizard.line"
    _description = "Sale payment option wizard line"

    wizard_id = fields.Many2one("sale.payment.option.wizard", required=True, ondelete="cascade")
    percentage = fields.Float(required=True)
    card_installment_id = fields.Many2one("account.card.installment", string="Installment Plan", required=True)
    surcharge_coefficient = fields.Float(related="card_installment_id.surcharge_coefficient")
    installment_qty = fields.Integer(related="card_installment_id.divisor")
    subtotal = fields.Monetary(compute="_compute_subtotal")
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    total_per_installment = fields.Monetary(compute="_compute_total_per_installment", string="Total per Installment")

    @api.depends("percentage", "wizard_id.total")
    def _compute_subtotal(self):
        lines = self.filtered(lambda line: line.percentage and line.wizard_id.total)
        for line in lines:
            line.subtotal = line.card_installment_id.map_installment_values(line.wizard_id.total * line.percentage).get(
                "amount"
            )
        (self - lines).subtotal = 0.0

    @api.depends("subtotal", "card_installment_id")
    def _compute_total_per_installment(self):
        lines = self.filtered(lambda line: line.subtotal and line.card_installment_id and line.installment_qty > 0)
        for line in lines:
            line.total_per_installment = line.subtotal / line.installment_qty
        (self - lines).total_per_installment = 0.0

    def get_json_dict(self, template_mode=False):
        self.ensure_one()
        digits = self.fields_get(["surcharge_coefficient"])["surcharge_coefficient"].get("digits", (16, 2))[1]
        surcharge = float_round((self.surcharge_coefficient - 1) * 100, precision_digits=digits)
        total_per_installment = (
            float_round(self.subtotal / self.installment_qty, precision_digits=2) if self.installment_qty else 0.0
        )
        if template_mode:
            return {
                "percentage": self.percentage * 100,
                "card_installment": self.card_installment_id.display_name,
                "card_installment_id": self.card_installment_id.id,
                "surcharge": surcharge,
                "installment_qty": self.installment_qty,
            }
        return {
            "percentage": self.percentage * 100,
            "card_installment": self.card_installment_id.display_name,
            "card_installment_id": self.card_installment_id.id,
            "surcharge": surcharge,
            "subtotal": self.subtotal,
            "total_per_installment": total_per_installment,
            "installment_qty": self.installment_qty,
        }

    def get_json_list(self, template_mode=False):
        return [line.get_json_dict(template_mode=template_mode) for line in self]
