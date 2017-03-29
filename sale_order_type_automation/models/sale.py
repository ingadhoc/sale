# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import api, models
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def run_invoicing_atomation(self):
        for so in self:
            invoicing_atomation = so.type_id.invoicing_atomation
            if invoicing_atomation != 'none':
                # we add this check just because if we call
                # action_invoice_create and nothing to invoice, it raise
                # an error
                if not any(
                        line.qty_to_invoice for line in so.order_line):
                    _logger.warning('Noting to invoice')
                    return True
                # a list is returned but only one invoice should be returned
                invoices = so.env['account.invoice'].browse(
                    self.action_invoice_create())
                # for any different from none and create_invoice, validate
                if invoices and invoicing_atomation != 'create_invoice':
                    invoices.signal_workflow('invoice_open')
                    # if different from validate, open and create, then
                    # pay it
                    if invoicing_atomation != 'validate_invoice':
                        for inv in invoices:
                            pay_context = {
                                'to_pay_move_line_ids': (
                                    inv.open_move_line_ids.ids),
                                # 'pop_up': True,
                                'default_company_id': inv.company_id.id,
                            }
                            payment_group = so.env[
                                'account.payment.group'].with_context(
                                pay_context).create({})
                            payment_group.payment_ids.create({
                                'payment_group_id': payment_group.id,
                                'payment_type': 'inbound',
                                'partner_type': 'customer',
                                'company_id': inv.company_id.id,
                                'partner_id': payment_group.partner_id.id,
                                'amount': payment_group.payment_difference,
                                'journal_id': so.type_id.payment_journal_id.id,
                                'payment_method_id': self.env.ref(
                                    'account.account_payment_method_manual_in'
                                ).id,
                            })
                            # if invoice_payment then we validate payment
                            if invoicing_atomation == 'invoice_payment':
                                payment_group.post()

    @api.multi
    def run_picking_atomation(self):
        for so in self:
            if so.type_id.picking_atomation == 'validate' and\
                    so.procurement_group_id:
                picking = self.env['stock.picking'].search(
                    [('group_id', '=', so.procurement_group_id.id)], limit=1)
                picking.force_assign()
                for pack in picking.pack_operation_ids:
                    if pack.product_qty > 0:
                        pack.write({'qty_done': pack.product_qty})
                    else:
                        pack.unlink()
                picking.do_transfer()

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        self.run_picking_atomation()
        self.run_invoicing_atomation()
        return res
