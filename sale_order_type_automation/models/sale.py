# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import api, models, _
from openerp.exceptions import ValidationError
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
                # usamos final para que reste adelantos y tmb por ej
                # por si se usa el modulo de facturar las returns
                invoices = so.env['account.invoice'].browse(
                    self.action_invoice_create(final=True))
                if invoices and invoicing_atomation == 'validate_invoice':
                    invoices.signal_workflow('invoice_open')

    @api.multi
    def run_picking_atomation(self):
        for so in self:
            procurement_group = so.procurement_group_id
            picking_atomation = so.type_id.picking_atomation
            picking = self.env['stock.picking'].search(
                [('group_id', '=', procurement_group.id)], limit=1)
            if so.type_id.book_id:
                picking.book_id = so.type_id.book_id
            if picking_atomation == 'validate' and procurement_group:
                picking.force_assign()
            if picking_atomation == 'validate_no_force' and procurement_group:
                products = []
                for move in picking.move_lines:
                    if move.state != 'assigned':
                        products.append(move.product_id)
                if products:
                    raise ValidationError(_(
                        'Products:\n%s\nAre not available, we suggest use'
                        ' another type of sale to generate a partial delivery.'
                    ) % ('\n'.join(x.name for x in products)))
            if picking_atomation in ['validate', 'validate_no_force'] and\
                    procurement_group:
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

    @api.multi
    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        if self.type_id.payment_atomation and self.type_id.payment_journal_id:
            res['pay_now_journal_id'] = self.type_id.payment_journal_id.id
        if self.type_id:
            res['sale_type_id'] = self.type_id.id
        return res
