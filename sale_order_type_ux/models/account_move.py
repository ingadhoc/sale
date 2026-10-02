##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _sale_order_type_ux_redetect_fiscal_position(self):
        """Redetect the fiscal position of the invoices that the order type moved to
        another company.

        ``_prepare_invoice`` only overrides ``company_id``, and the rest of the values it
        returns —the fiscal position and the taxes on each line— were computed for the
        company that sells. Given explicitly on create, no compute replaces them, so the
        invoice is born in the branch carrying the parent's taxes.

        Same two steps as the change company wizard of ``account_multicompany_ux``: the
        write recomputes the fiscal position but not the taxes, so the taxes are updated
        with the method behind the "Update Taxes" button, and only when the position
        actually changed, because it recomputes them from the product and discards the
        ones set by hand.
        """
        for move in self:
            orders = move.invoice_line_ids.sale_line_ids.order_id
            if not orders or move.company_id in orders.company_id:
                continue
            old_fiscal_position = move.fiscal_position_id
            move.with_company(move.company_id)._compute_fiscal_position_id()
            if move.state == "draft" and move.fiscal_position_id != old_fiscal_position:
                move.action_update_fpos_values()
