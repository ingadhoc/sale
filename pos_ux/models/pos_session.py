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

    def _pos_ux_cannot_close_session(self):
        """Own check: 20.0 removed the core _cannot_close_session hook."""
        self.ensure_one()
        if self.config_id.billing_behavior == "invoice_required":
            pending = self._paid_orders_without_invoice()
            if pending:
                return {
                    "status": False,
                    "type": "pos_ux_unbilled",
                    "message": self.env._(
                        "Cannot close the session: there are %s paid order(s) "
                        "without invoice. Invoice them from the backend "
                        '("Generate invoices" button).',
                        len(pending),
                    ),
                    "redirect": False,
                }
        return {}

    def close_session_from_ui(self, *args, **kwargs):
        blocked = self._pos_ux_cannot_close_session()
        if blocked:
            return blocked
        return super().close_session_from_ui(*args, **kwargs)

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ["invoice_contingency"]
