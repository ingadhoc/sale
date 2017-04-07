# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import api, models
import logging

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.onchange('sale_type_id')
    def onchange_sale_type_set_pay_now(self):
        # if self.sale_type_id.payment_term_id:
        #     self.payment_term = self.sale_type_id.payment_term_id.id
        # if self.sale_type_id.journal_id:
        #     self.journal_id = self.sale_type_id.journal_id.id
        if self.sale_type_id.payment_atomation != 'none' and self.sale_type_id.payment_journal_id:
            self.pay_now_journal_id = self.sale_type_id.payment_journal_id.id
        else:
            self.pay_now_journal_id = False

    # @api.multi
    # def run_payment_atomation(self):
    #     for rec in self:
    #         payment_atomation = rec.sale_type_id.payment_atomation
    #         if payment_atomation != 'none' and rec.type in [
    #                 'out_invoice', 'out_refund']:
    #             pay_context = {
    #                 'to_pay_move_line_ids': (rec.open_move_line_ids.ids),
    #                 # 'pop_up': True,
    #                 'default_company_id': rec.company_id.id,
    #             }
    #             payment_group = rec.env[
    #                 'account.payment.group'].with_context(
    #                     pay_context).create({})
    #             payment_group.payment_ids.create({
    #                 'payment_group_id': payment_group.id,
    #                 'payment_type': 'inbound',
    #                 'partner_type': 'customer',
    #                 'company_id': rec.company_id.id,
    #                 'partner_id': payment_group.partner_id.id,
    #                 'amount': payment_group.payment_difference,
    #                 'journal_id': rec.sale_type_id.payment_journal_id.id,
    #                 'payment_method_id': self.env.ref(
    #                     'account.account_payment_method_manual_in'
    #                 ).id,
    #             })
    #             # if invoice_payment then we validate payment
    #             if payment_atomation == 'validate_payment':
    #                 payment_group.post()
