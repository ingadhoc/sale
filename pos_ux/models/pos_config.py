import hashlib
import re

from odoo import api, fields, models
from odoo.exceptions import UserError

POS_ASSETS_BUNDLE = "point_of_sale.assets_prod"
ASSETS_VERSION_PARAM = "pos_ux.notified_assets_version"


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

    @api.model
    def get_pos_assets_version(self):
        """Stamp of the POS screen files, as served right now by the server.

        It changes whenever the assets bundle is rebuilt (any module update that
        touches the POS), unlike the Odoo version, which stays on "19.0".
        """
        links = self.env["ir.qweb"]._get_asset_links(POS_ASSETS_BUNDLE, css=False, js=True)
        for link in links:
            # The stamp is the unique of /web/assets/<unique>/<bundle>.min.js, the
            # same one the register reads from the script tag it is running.
            match = re.match(r"/web/assets/([^/]+)/", link)
            if match and POS_ASSETS_BUNDLE in link:
                return match.group(1)
        return hashlib.sha1("|".join(links).encode()).hexdigest()[:16]

    @api.model
    def notify_outdated_pos_sessions(self):
        """Tell every open register that the POS files changed (cron)."""
        param = self.env["ir.config_parameter"].sudo()
        version = self.get_pos_assets_version()
        previous = param.get_param(ASSETS_VERSION_PARAM)
        if previous == version:
            return False
        param.set_param(ASSETS_VERSION_PARAM, version)
        if not previous:
            # First run: nothing to compare against, so nobody is outdated yet.
            return False
        configs = self.env["pos.session"].search([("state", "!=", "closed")]).config_id
        for config in configs:
            config._notify("POS_UX_ASSETS_VERSION", {"version": version})
        return bool(configs)
