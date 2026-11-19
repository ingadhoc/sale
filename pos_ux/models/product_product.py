from odoo import _, models
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = "product.product"

    def write(self, vals):
        if not vals.get("active", True):
            self._check_no_open_pos_session_to_archive()
        return super().write(vals)

    def _check_no_open_pos_session_to_archive(self):
        """Block archiving a variant still sold in POS while a session is open.

        `product.template._create_variant_ids()` falls back to a direct
        `write({'active': False})` (via `_unlink_or_archive`) when it can't
        unlink a variant made obsolete by an attribute change — bypassing
        `action_archive()` and its `_ensure_unused_in_pos()` guard. A POS
        terminal with that variant cached then silently substitutes it by
        the template's default variant on sale.
        """
        archiving = self.filtered(lambda product: product.active and product.available_in_pos)
        if archiving and self.env["pos.session"].sudo().search_count([("state", "!=", "closed")]):
            raise UserError(
                _(
                    "Cannot archive %s: there is an open Point of Sale session that could "
                    "still sell it. Close all sessions first.",
                    ", ".join(archiving.mapped("display_name")),
                )
            )
