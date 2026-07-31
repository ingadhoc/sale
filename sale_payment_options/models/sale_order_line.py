from odoo import models
from odoo.tools import float_is_zero


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_payment_options_installments(self):
        """Installment breakdown of this line, one entry per order payment option.

        Every entry is the list of segments of that payment option, so an option split
        across plans (e.g. 50% in 3 installments + 50% in 6) keeps its segments together.
        Surcharge and installment quantity are read from ``options_json`` so the printed
        amounts match the option as it was quoted. Installments are always computed on
        the line amount taxes included, no matter how the report prints the line, because
        they are what the customer is going to pay, just like the order wide table.
        """
        self.ensure_one()
        base_amount = self.price_total
        if not base_amount:
            return []

        options = []
        for option in self.order_id.payment_option_ids:
            segments = []
            for item in option.options_json or []:
                installment_qty = item.get("installment_qty") or 0
                percentage = item.get("percentage") or 0.0
                if not installment_qty or not percentage:
                    continue
                surcharge_coefficient = 1.0 + (item.get("surcharge") or 0.0) / 100.0
                amount = base_amount * percentage / 100.0 * surcharge_coefficient
                segments.append(
                    {
                        "percentage": percentage,
                        "installment_qty": installment_qty,
                        "amount_per_installment": amount / installment_qty,
                    }
                )
            if segments:
                options.append(segments)
        return options

    def _get_payment_options_installments_display(self):
        """Human readable installment breakdown, e.g. "3 installments of $ 30,000.00 | 6 installments of $ 15,000.00".

        Options are separated by a pipe; segments of a single option split across plans are joined with a plus.
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
                segments_display.append(
                    self.env._(
                        "%(installment_qty)s installments of %(amount)s",
                        installment_qty=segment["installment_qty"],
                        amount=currency.format(segment["amount_per_installment"]),
                    )
                )
            if segments_display:
                options_display.append(" + ".join(segments_display))
        return " | ".join(options_display)
