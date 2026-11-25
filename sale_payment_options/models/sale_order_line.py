from odoo import models
from odoo.tools import float_is_zero


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_payment_options_installments(self):
        """Installment breakdown of this line, one entry per order payment option.

        Every entry is the list of segments of that payment option, so an option split
        across plans (e.g. 50% in 3 installments + 50% in 6) keeps its segments together.
        Installments are always computed on the line amount taxes included, no matter how the
        report prints the line, because they are what the customer is going to pay, just like
        the order wide table.
        """
        self.ensure_one()
        base_amount = self.price_total
        if not base_amount:
            return []

        options = []
        for option in self.order_id.payment_option_ids._grouped_by_option():
            segments = []
            for row in option:
                if not row.installment_qty or not row.percentage:
                    continue
                surcharge_coefficient = row.card_installment_id.surcharge_coefficient
                amount = base_amount * row.percentage * surcharge_coefficient
                segments.append(
                    {
                        "percentage": row.percentage * 100,
                        "installment_qty": row.installment_qty,
                        "amount_per_installment": amount / row.installment_qty,
                        "card_installment": row.card_installment_id.display_name or "",
                    }
                )
            if segments:
                options.append(segments)
        return options

    def _get_payment_options_installments_display(self):
        """Human readable installment breakdown, e.g. "Plan A (CASH): 1 installments of $ 90,000.00 | Plan B (CARD): 6 installments of $ 15,000.00".

        Each segment is prefixed with the name of its installment plan, so the customer knows which
        payment method each amount belongs to. Options are separated by a pipe; segments of a single
        option split across plans are joined with a plus.
        """
        self.ensure_one()
        currency = self.order_id.currency_id
        rounding = currency.rounding or 0.01
        options_display = []
        for segments in self._get_payment_options_installments():
            segments_display = []
            for segment in segments:
                if float_is_zero(segment["amount_per_installment"], precision_rounding=rounding):
                    continue
                installment_display = self.env._(
                    "%(installment_qty)s installments of %(amount)s",
                    installment_qty=segment["installment_qty"],
                    amount=currency.format(segment["amount_per_installment"]),
                )
                if segment["card_installment"]:
                    installment_display = self.env._(
                        "%(card_installment)s: %(installments)s",
                        card_installment=segment["card_installment"],
                        installments=installment_display,
                    )
                segments_display.append(installment_display)
            if segments_display:
                options_display.append(" + ".join(segments_display))
        return " | ".join(options_display)
