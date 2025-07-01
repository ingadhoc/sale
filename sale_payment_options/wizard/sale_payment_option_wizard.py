from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SalePaymentOptionWizard(models.TransientModel):
    _name = "sale.payment.option.wizard"
    _description = "Sale payment option wizard"

    sale_order_id = fields.Many2one("sale.order", string="Sales Order")
    payment_option_template_id = fields.Many2one("sale.payment.option.template")
    total = fields.Monetary(string="Order Total", related="sale_order_id.amount_total")
    currency_id = fields.Many2one("res.currency", string="Currency", related="sale_order_id.currency_id")
    line_ids = fields.One2many("sale.payment.option.wizard.line", "wizard_id", string="Payment Lines")

    @api.constrains("line_ids")
    def _check_percentages(self):
        for wizard in self:
            percentage_total = sum(line.percentage for line in wizard.line_ids)
            if percentage_total != 1:
                raise ValidationError(_("The sum of the percentages must be exactly 100."))

    def confirm(self):
        self.ensure_one()
        template_mode = bool(self.payment_option_template_id)
        options = self.line_ids.get_json_list(template_mode=template_mode)
        vals = {
            "options_json": options,
        }
        if self.sale_order_id:
            vals["sale_order_id"] = self.sale_order_id.id
        if self.payment_option_template_id:
            vals["payment_option_template_id"] = self.payment_option_template_id.id
        self.env["sale.payment.option"].create(vals)
        return {"type": "ir.actions.act_window_close"}
