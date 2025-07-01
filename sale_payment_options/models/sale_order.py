from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_option_ids = fields.One2many(
        "sale.payment.option",
        "sale_order_id",
        string="Payment Options",
    )
    payment_option_template_id = fields.Many2one("sale.payment.option.template", string="Payment Option Template")

    def action_open_payment_option_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.payment.option.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_sale_order_id": self.id,
            },
        }

    @api.onchange("payment_option_template_id")
    def _onchange_payment_option_template_id(self):
        if not self.payment_option_template_id:
            self.payment_option_ids = [fields.Command.clear()]
            return

        invalid_options = []
        for option in self.payment_option_template_id.payment_option_ids:
            total_percentage = sum(opt.get("percentage") for opt in option.options_json)
            if abs(total_percentage - 100) > 0.01:
                option_names = [opt.get("card_installment") for opt in option.options_json]
                invalid_options.append(f"{', '.join(option_names)}: {total_percentage}%")

        if invalid_options:
            return {
                "warning": {
                    "title": _("Invalid Template Configuration"),
                    "message": _("The following options don't sum to 100%%:\n%s") % "\n".join(invalid_options),
                }
            }

        self.payment_option_ids = [fields.Command.clear()]
        for option in self.payment_option_template_id.payment_option_ids:
            self._create_payment_option_from_template(option)

    def _create_payment_option_from_template(self, template_option):
        wizard_lines = [
            (
                0,
                0,
                {
                    "card_installment_id": opt.get("card_installment_id"),
                    "percentage": opt.get("percentage") / 100,
                },
            )
            for opt in template_option.options_json
        ]
        wizard = self.env["sale.payment.option.wizard"].create(
            {
                "sale_order_id": self._origin.id,
                "line_ids": wizard_lines,
            }
        )
        wizard.confirm()

    @api.constrains("payment_option_ids")
    def _check_payment_options_percentages(self):
        for order in self:
            invalid_options = []
            for option in order.payment_option_ids:
                if option.options_json:
                    total_percentage = sum(opt.get("percentage") for opt in option.options_json)
                    if abs(total_percentage - 100) > 0.01:
                        option_names = [opt.get("card_installment") for opt in option.options_json]
                        invalid_options.append(f"'{', '.join(option_names)}': {total_percentage}%")

            if invalid_options:
                raise ValidationError(
                    _("The following payment options have invalid percentage totals (must be exactly 100%%):\n%s")
                    % "\n".join(invalid_options)
                )
