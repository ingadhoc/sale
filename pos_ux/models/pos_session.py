from odoo import api, fields, models


class PosSession(models.Model):
    _inherit = "pos.session"

    invoice_contingency = fields.Boolean(tracking=True)

    def _paid_orders_without_invoice(self):
        return self.order_ids.filtered(lambda o: o.state == "paid" and not o.account_move)

    def action_generate_invoices(self):
        self._paid_orders_without_invoice()._generate_pos_order_invoice()

    def pos_toogle_contingency_mode(self):
        self.ensure_one()
        if self.invoice_contingency:
            self.action_unset_invoice_contingency()
        else:
            self.action_set_invoice_contingency()
        return self.invoice_contingency

    def action_set_invoice_contingency(self):
        self.invoice_contingency = True

    def action_unset_invoice_contingency(self):
        self.invoice_contingency = False

    def _cannot_close_session(self, bank_payment_method_diffs=None):
        if self.config_id.billing_behavior == "invoice_required":
            pending = self._paid_orders_without_invoice()
            if pending:
                return {
                    "successful": False,
                    "message": self.env._(
                        "Cannot close the session: there are %s paid order(s) "
                        "without invoice. Invoice them from the backend "
                        '("Generate invoices" button).',
                        len(pending),
                    ),
                    "redirect": False,
                    "pos_ux_unbilled": True,
                }
        return super()._cannot_close_session(bank_payment_method_diffs=bank_payment_method_diffs)

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ["invoice_contingency"]

    def _closing_diff_move_refs(self, payment_method):
        """Every reference the closing difference move could have been saved under.

        The reference is translated when the move is created, so the language of
        the user that closed the session is unknown at read time.
        """
        self.ensure_one()
        langs = {code for code, dummy in self.env["res.lang"].get_installed()}
        langs.add("en_US")
        return sorted(
            {
                self.with_context(lang=lang)._get_diff_account_move_ref(payment_method.with_context(lang=lang))
                for lang in langs
            }
        )
