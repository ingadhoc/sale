##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from markupsafe import Markup
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _background_post_available(self):
        return "background_post" in self._fields and hasattr(self, "_get_background_post_batch_size")

    def _prepare_dict_account_payment(self, invoice, payment_journal):
        return {
            # reconciled_invoice_ids is a non stored computed field without inverse, so
            # writing it here was a no-op. invoice_ids is the stored m2m holding the link
            "invoice_ids": [(6, 0, invoice.ids)],
            "amount": invoice.amount_residual,
            "partner_id": invoice.partner_id.id,
            "partner_type": "customer" if invoice.is_sale_document() else "supplier",
            # refunds move the money on the opposite direction of the document they fix,
            # otherwise a customer refund would be registered as an inbound receipt
            "payment_type": "inbound" if invoice.is_inbound() else "outbound",
            # the payment must live in the invoice company (a branch may invoice while the
            # shared payment journal belongs to the parent). Company consistency checks use
            # parent_of semantics, so a payment on the branch can still use the parent journal,
            # but a payment left on the journal's parent company can't reference the branch lines
            "company_id": invoice.company_id.id,
            "journal_id": payment_journal.id,
            "date": fields.Date.context_today(self),
            "currency_id": invoice.currency_id.id,
        }

    def _register_payment_invoice(self, invoice, payment_journal):
        # resolve company-dependent defaults/computes against the invoice company (branch)
        payment = (
            self.env["account.payment"]
            .with_company(invoice.company_id)
            .create(self._prepare_dict_account_payment(invoice, payment_journal))
        )
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
                invoice.message_post(body=message)
        return res

    def _notify_background_post_error(self, error):
        self.ensure_one()
        orders = self.sudo().line_ids.sale_line_ids.order_id
        if not orders:
            return super()._notify_background_post_error(error)
        body = self._get_background_post_error_body(error)
        for order in orders:
            order.message_post(body=body, partner_ids=order._get_internal_message_partners().ids)
        self._message_log(
            body=self.env._(
                "We tried to validate this invoice on the background but got an error, logged on %(orders)s.",
                orders=Markup(", ").join(order._get_html_link() for order in orders),
            )
        )
