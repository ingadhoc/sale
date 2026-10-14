from odoo import fields, models


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
    default_order_partner_id = fields.Many2one(
        "res.partner",
        string="Default Order Customer",
        help=(
            "If set, every new POS order will start with this partner pre-selected. "
            "Useful for B2C points of sale where most sales go to a generic "
            "anonymous customer (e.g. 'Consumidor Final' in AR)."
        ),
    )

    def get_limited_partners_loading(self, offset=0):
        partner_ids = super().get_limited_partners_loading(offset)
        if self.default_order_partner_id and (self.default_order_partner_id.id,) not in partner_ids:
            partner_ids.append((self.default_order_partner_id.id,))
        return partner_ids
