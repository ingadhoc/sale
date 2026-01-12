##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("sale_type_id")
    def onchange_sale_type_set_pay_now(self):
        if self.sale_type_id.payment_atomation != "none" and self.sale_type_id.payment_journal_id:
            self.pay_now_journal_id = self.sale_type_id.payment_journal_id.id
        else:
            self.pay_now_journal_id = False

    def _compute_company_id(self):
        super()._compute_company_id()
        # If company_id is empty after super (because _accessible_branches returned empty),
        # assign the journal's company directly. This happens when in sudo mode and the user
        # has no access to any company
        for move in self.filtered(lambda m: not m.company_id):
            sale_type_id = self.env["sale.order.type"].browse(self.env.context.get("sale_type_id")) or move.sale_type_id  # noqa

            if sale_type_id.journal_id and sale_type_id.invoicing_atomation != "none":
                move.company_id = sale_type_id.journal_id.company_id
