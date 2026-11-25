from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_option_ids = fields.One2many(
        "sale.payment.option",
        "sale_order_id",
        string="Payment Options",
    )
    payment_option_template_id = fields.Many2one("sale.payment.option.template", string="Payment Option Template")

    @api.onchange("payment_option_template_id")
    def _onchange_payment_option_template_id(self):
        """Load the template options in memory, the way sale_management loads an order template.

        Nothing is written here: creating the rows from the onchange is what made a discarded
        quotation keep the template options, and print them twice. Clearing the field leaves the
        loaded options alone, also like an order template.
        """
        if not self.payment_option_template_id:
            return

        self.payment_option_ids = [fields.Command.clear()] + [
            fields.Command.create(option._prepare_payment_option_values())
            for option in self.payment_option_template_id.payment_option_ids
        ]

    @api.constrains("payment_option_ids")
    def _check_payment_options_percentages(self):
        """Also on the order, so deleting part of an option does not leave the rest under 100%."""
        for order in self:
            order.payment_option_ids._check_payment_options_percentages()
