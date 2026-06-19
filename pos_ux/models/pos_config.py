from odoo import fields, models
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = "pos.config"

    billing_behavior = fields.Selection(
        [
            ("on_demand", "Invoice on demand"),
            ("invoice_by_default", "By default invoice"),
            ("invoice_required", "allways Invoice"),
        ],
        default="on_demand",
    )
    block_invoice_download = fields.Boolean()
    default_partner_id = fields.Many2one(
        "res.partner",
        string="Default Customer",
        help=(
            "If set, every new POS order will start with this partner pre-selected. "
            "Useful for B2C points of sale where most sales go to a generic "
            "anonymous customer (e.g. 'Consumidor Final' in AR)."
        ),
    )

    def get_limited_partners_loading(self, offset=0):
        partner_ids = super().get_limited_partners_loading(offset)
        if self.default_partner_id and (self.default_partner_id.id,) not in partner_ids:
            partner_ids.append((self.default_partner_id.id,))
        return partner_ids

    def open_ui(self):
        for config in self:
            invalid_payment_methods = config.payment_method_ids.filtered(
                lambda method: not method.split_transactions and not method.receivable_account_id
            )
            if invalid_payment_methods:
                payment_method_names = ", ".join(invalid_payment_methods.mapped("name"))
                raise UserError(
                    self.env._(
                        "No se puede completar la operación: falta definir cuenta intermediaria en los siguientes métodos de pago: %s",
                        payment_method_names,
                    )
                )
            payment_method_without_outstanding_account = config.payment_method_ids.filtered(
                lambda method: method.journal_id.type == "bank"
                and not method.outstanding_account_id
                and not any(line.payment_account_id for line in method.journal_id.inbound_payment_method_line_ids)
            )
            if payment_method_without_outstanding_account:
                payment_method_without_outstanding_account_names = ", ".join(
                    payment_method_without_outstanding_account.mapped("name")
                )
                raise UserError(
                    self.env._(
                        "No se puede completar la operación: falta definir la cuenta pendiente en los siguientes métodos de pago: %s",
                        payment_method_without_outstanding_account_names,
                    )
                )
        return super().open_ui()
