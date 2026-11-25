from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_round


class SalePaymentOption(models.Model):
    _name = "sale.payment.option"
    _description = "Sale payment option"
    _order = "option_number, sequence, id"

    sequence = fields.Integer(default=10)
    payment_option_template_id = fields.Many2one("sale.payment.option.template", ondelete="cascade")
    sale_order_id = fields.Many2one("sale.order", ondelete="cascade", index="btree_not_null")
    # Rows sharing a number are one payment option: that is how an option combines plans
    # (50% on debit and 50% in six installments), and the number is the one the report prints.
    option_number = fields.Integer(string="Op.", default=0)
    card_installment_id = fields.Many2one("account.card.installment", string="Installment Plan", required=True)
    percentage = fields.Float(string="% of Order", default=1.0, digits=(16, 4))
    currency_id = fields.Many2one(related="sale_order_id.currency_id")
    installment_qty = fields.Integer(related="card_installment_id.divisor", string="Installments")
    surcharge = fields.Float(compute="_compute_surcharge")
    amount_subtotal = fields.Monetary(compute="_compute_amounts", string="Subtotal")
    amount_per_installment = fields.Monetary(compute="_compute_amounts", string="Amount per Installment")
    option_percentage_total = fields.Float(
        compute="_compute_option_percentage_total",
        string="Option Total %",
        help="What the whole option adds up to. An option that is not at 100% cannot be saved.",
    )
    option_percentage_invalid = fields.Boolean(compute="_compute_option_percentage_total")

    @api.depends("card_installment_id.surcharge_coefficient")
    def _compute_surcharge(self):
        for rec in self:
            coefficient = rec.card_installment_id.surcharge_coefficient
            # Rounded here, not only on screen: the report prints this value as it is, and a 1.04
            # coefficient gives 4.000000000000036 straight from the subtraction
            rec.surcharge = float_round((coefficient - 1) * 100, precision_digits=2) if coefficient else 0.0

    @api.depends("percentage", "card_installment_id", "sale_order_id.amount_total")
    def _compute_amounts(self):
        """Amounts of this row, recomputed as the quotation is edited.

        They are not stored on purpose: the point of the tab is to follow the order total while it
        is being edited, without waiting for a save. A template row has no order, so it has no
        amounts either.
        """
        for rec in self:
            base_amount = rec.sale_order_id.amount_total * rec.percentage
            if not rec.card_installment_id or not base_amount:
                rec.amount_subtotal = 0.0
                rec.amount_per_installment = 0.0
                continue
            amount = rec.card_installment_id.map_installment_values(base_amount).get("amount")
            rec.amount_subtotal = amount
            rec.amount_per_installment = amount / rec.installment_qty if rec.installment_qty else 0.0

    @api.depends(
        "option_number",
        "percentage",
        "sale_order_id.payment_option_ids.percentage",
        "sale_order_id.payment_option_ids.option_number",
        "payment_option_template_id.payment_option_ids.percentage",
        "payment_option_template_id.payment_option_ids.option_number",
    )
    def _compute_option_percentage_total(self):
        """Shown in the list so an option that does not add up to 100% is visible before saving."""
        for rec in self:
            total = sum(rec._option_siblings().mapped("percentage"))
            rec.option_percentage_total = total
            rec.option_percentage_invalid = bool(float_compare(total, 1.0, precision_digits=4))

    @api.onchange("card_installment_id")
    def _onchange_card_installment_id(self):
        """A row added by hand is an option of its own: one plan per option is the usual case.

        The row numbers itself, instead of the order numbering its rows: an onchange on the order
        that writes into payment_option_ids makes the web client keep the row it already had and
        add the one the server sends back, so one added row ended up as two.
        """
        if not self.option_number:
            self.option_number = self._container_options()._next_option_number()

    def _option_siblings(self):
        """Every row of the same option, this one included."""
        self.ensure_one()
        container = self._container_options()
        return container.filtered(lambda rec: rec.option_number == self.option_number) or self

    def _container_options(self):
        """All the rows of the order or the template this row belongs to."""
        self.ensure_one()
        return self.sale_order_id.payment_option_ids or self.payment_option_template_id.payment_option_ids or self

    @api.constrains("percentage", "option_number", "card_installment_id")
    def _check_option_percentage(self):
        containers = self.sale_order_id.payment_option_ids | self.payment_option_template_id.payment_option_ids
        containers._check_payment_options_percentages()

    def _check_payment_options_percentages(self):
        """Each option has to add up to 100% of the order, on quotations and on templates alike."""
        invalid_options = []
        for option in self._grouped_by_option():
            total = sum(option.mapped("percentage"))
            if float_compare(total, 1.0, precision_digits=4):
                invalid_options.append(
                    _("Option %(number)s adds up to %(total)s%%", number=option[0].option_number, total=total * 100)
                )
        if invalid_options:
            raise ValidationError(
                _("Every payment option has to add up to 100%% of the order:\n%s") % "\n".join(invalid_options)
            )

    def _grouped_by_option(self):
        """This recordset grouped into options, in the order the report prints them."""
        groups = {}
        for rec in self:
            groups.setdefault(rec.option_number, self.browse())
            groups[rec.option_number] |= rec
        return [groups[number] for number in sorted(groups)]

    def _next_option_number(self):
        """The number a row added to this recordset gets: an option of its own, after the others."""
        return max(self.mapped("option_number"), default=0) + 1

    def _prepare_payment_option_values(self):
        """Values to copy a template row onto a quotation. A template carries no amounts."""
        self.ensure_one()
        return {
            "sequence": self.sequence,
            "option_number": self.option_number,
            "card_installment_id": self.card_installment_id.id,
            "percentage": self.percentage,
        }
