##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.onchange('sale_type_id')
    def onchange_sale_type_set_pay_now(self):
        if (self.sale_type_id.payment_atomation != 'none' and
                self.sale_type_id.payment_journal_id):
            self.pay_now_journal_id = self.sale_type_id.payment_journal_id.id
        else:
            self.pay_now_journal_id = False

    def _compute_sale_type_id(self):
        # If create invoice from stock.picking (e.g. when we return and we have automated to create the invoice), sale type will not computed.
        if self.env.context.get("active_model", False) == "stock.picking":
            return
        super()._compute_sale_type_id()
