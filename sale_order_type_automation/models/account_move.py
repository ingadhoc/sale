##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


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

<<<<<<< 92a268dbfba4f2b4b51054108cc07533e6f08bcc
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
            and x.sale_type_id.payment_atomation == "validate_payment"
        ):
            try:
                self._register_payment_invoice(invoice, invoice.sale_type_id.payment_journal_id)
            except Exception as error:
                message = "Could not automatically create and validate payment. Error: %s" % error
                invoice.message_post(body=message)
        return res
||||||| 3da0cf614caff1162b31c37b0692599831fecc87
    def _compute_company_id(self):
        super()._compute_company_id()
        # If company_id is empty after super (because _accessible_branches returned empty),
        # assign the journal's company directly. This happens when in sudo mode and the user
        # has no access to any company
        for move in self.filtered(
            lambda m: not m.company_id and m.sale_type_id.journal_id and m.sale_type_id.invoicing_atomation != "none"
        ):
            move.company_id = move.sale_type_id.journal_id.company_id
=======
    def _compute_company_id(self):
        super()._compute_company_id()
        # If company_id is empty after super (because _accessible_branches returned empty),
        # assign the journal's company directly. This happens when in sudo mode and the user
        # has no access to any company
        for move in self.filtered(lambda m: not m.company_id):
            sale_type_id = self.env["sale.order.type"].browse(self.env.context.get("sale_type_id")) or move.sale_type_id  # noqa

            if sale_type_id.journal_id and sale_type_id.invoicing_atomation != "none":
                move.company_id = sale_type_id.journal_id.company_id
>>>>>>> f2dd1eaaab9e0a0fc8b2b6ed059af7644c879fa6
