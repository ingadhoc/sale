##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging

import psycopg2
from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _prepare_dict_account_payment(self, invoice, payment_journal):
        partner_type = invoice.move_type in ("out_invoice", "out_refund") and "customer" or "supplier"
        return {
            "reconciled_invoice_ids": [(6, 0, invoice.ids)],
            "amount": invoice.amount_residual,
            "partner_id": invoice.partner_id.id,
            "partner_type": partner_type,
            "journal_id": payment_journal.id,
            "date": fields.Date.context_today(self),
            "currency_id": invoice.currency_id.id,
        }

    def _register_payment_invoice(self, invoice, payment_journal):
        payment = self.env["account.payment"].create(self._prepare_dict_account_payment(invoice, payment_journal))
        payment.action_post()

        domain = [
            ("account_type", "in", ("asset_receivable", "liability_payable")),
            ("reconciled", "=", False),
        ]
        payment_lines = payment.move_id.line_ids.filtered_domain(domain)
        lines = invoice.line_ids
        for account in payment_lines.account_id:
            (payment_lines + lines).filtered_domain(
                [("account_id", "=", account.id), ("reconciled", "=", False)]
            ).reconcile()
        return payment

    def action_post(self):
        res = super().action_post()
        for invoice in self.filtered(
            lambda x: x.move_type in ("out_invoice", "out_refund", "in_invoice", "in_refund")
            and x.state == "posted"
            and x.payment_state in ("not_paid", "partial")
            and x.sale_type_id.payment_atomation == "validate_payment"
        ):
            try:
                self._register_payment_invoice(invoice, invoice.sale_type_id.payment_journal_id)
            except Exception as error:
                message = "Could not automatically create and validate payment. Error: %s" % error
                try:
                    invoice.message_post(body=message)
                except psycopg2.Error:
                    invoice.env.cr.rollback()
                    _logger.warning(
                        "The payment automation transaction of invoice %s was "
                        "aborted, recovering before logging the failure: %s",
                        invoice.ids,
                        error,
                    )
                    invoice.message_post(body=message)
        return res
