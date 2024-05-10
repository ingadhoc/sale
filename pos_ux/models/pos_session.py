from odoo import models, fields, api


class PosSession(models.Model):

    _inherit = 'pos.session'

    invoice_contingency = fields.Boolean(tracking=True,)

    def action_generate_invoices(self):
        self.order_ids.filtered(lambda x: x.state == 'paid' and not x.account_move)._generate_pos_order_invoice()

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

    def _loader_params_pos_session(self):
        params = super()._loader_params_pos_session()
        params['search_params']['fields'].append('invoice_contingency')
        return params

    def _validate_session(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        """
            Agrego este contexto para evitar el bloqueo en los modulos saas.
        """
        return super(PosSession, self.with_context(allow_no_partner=True))._validate_session(balancing_account=balancing_account, amount_to_balance=amount_to_balance, bank_payment_method_diffs=bank_payment_method_diffs)
