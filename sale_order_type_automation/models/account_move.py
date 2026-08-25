##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_invoicing_automation_blocking_reasons(self):
        """Return ``{move.id: reason}`` for invoices that must not be posted automatically.

        These are the failures that can be known BEFORE calling ``action_post``. Trying
        and failing is not harmless: ``_post`` writes ``state`` before the constraints
        run and nothing rolls that write back, so the next flush persists a move that is
        'posted' with no number and no document type. Skipping the post leaves a clean
        draft plus an explanatory log instead, which is the same treatment the invoices
        excluded by ``invoice_validate_domain`` already get.
        """
        reasons = {}
        # soft dependency: only latam localizations require a document type
        if "l10n_latam_document_type_id" not in self._fields:
            return reasons
        for move in self.filtered(lambda x: x.l10n_latam_use_documents and not x.l10n_latam_document_type_id):
            reason = _(
                "The journal '%(journal)s' requires a document type and none could be " "determined for %(partner)s.",
                journal=move.journal_id.display_name,
                partner=move.partner_id.display_name,
            )
            responsibility_field = "l10n_ar_afip_responsibility_type_id"
            if responsibility_field in move.partner_id._fields and not move.partner_id[responsibility_field]:
                reason += _(" Please configure the ARCA Responsibility of the customer.")
            reasons[move.id] = reason
        return reasons

    def _recover_failed_automatic_post(self):
        """Undo the state a failed ``action_post`` left behind on these invoices.

        ``_post`` writes ``state`` through ``write()``, which validates the constraints
        only after updating the cache, so a constraint error leaves ``state = 'posted'``
        pending and the next flush (the failure log itself) persists it: a posted move
        with no number and no document type. Wrapping the post in a savepoint is not an
        option here, the AR e-invoice code commits and discards it (ingadhoc/sale#1755),
        so we only put back the moves left in that impossible shape, which by definition
        never reached numbering nor the CAE.
        """
        broken = self.filtered(lambda x: x.state == "posted" and x.name in (False, "/"))
        if not broken:
            return
        try:
            broken.sudo().write({"state": "draft", "posted_before": False})
        except Exception as recovery_error:
            # never mask the original error: writing on a posted move checks the lock dates
            message = "Could not restore the draft state of this invoice. Error: %s" % recovery_error
            broken._message_log_batch(bodies=dict.fromkeys(broken.ids, message))

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
