# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import api, models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for so in self:
            if so.type_id.validate_automatically_picking and\
                    so.procurement_group_id:
                picking = self.env['stock.picking'].search(
                    [('group_id', '=', so.procurement_group_id.id)], limit=1)
                picking.force_assign()
                picking.do_transfer()
            if so.type_id.journal_id:
                invoice_id = self.action_invoice_create()
                if so.type_id.validate_automatically_invoice:
                    so.env['account.invoice'].browse(
                        invoice_id).signal_workflow('invoice_open')
                if so.type_id.payment_journal_id:
                    inv = self.env['account.invoice'].browse(invoice_id)
                    if inv:
                        amount = inv.type in (
                            'out_refund', 'in_refund') and -inv.residual or \
                            inv.residual
                        payment = self.env['account.payment'].create({
                            'partner_type': 'customer',
                            'amount': amount,
                            'invoice_ids': [(6, 0, [inv.id])],
                            'payment_date': fields.Date.context_today(self),
                            'journal_id': so.type_id.payment_journal_id.id,
                            'destination_account_id':
                            inv.partner_id.property_account_receivable_id.id,
                            'partner_id': self.env[
                                'res.partner']._find_accounting_partner(
                                inv.partner_id).id,
                            'payment_method_id': self.env.ref(
                                'account.account_payment_method_manual_in').id,
                            'payment_type': 'inbound'
                        })
                        if so.type_id.validate_automatically_payment:
                            payment.post()
                            if so.type_id.validate_automatically_picking:
                                so.action_done()

        return res
