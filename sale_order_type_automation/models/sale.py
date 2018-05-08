# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import api, models, fields, _
from openerp.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # TODO move this to a usability module or sale_order_type module
    type_id = fields.Many2one(
        track_visibility='onchange',
        readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
    )

    @api.multi
    def run_invoicing_atomation(self):
        for rec in self.filtered(
                lambda x: x.type_id.invoicing_atomation != 'none'):
            # we add this check just because if we call
            # action_invoice_create and nothing to invoice, it raise
            # an error
            if not any(
                    line.qty_to_invoice for line in rec.order_line):
                _logger.warning('Noting to invoice')
                return True
            # a list is returned but only one invoice should be returned
            # usamos final para que reste adelantos y tmb por ej
            # por si se usa el modulo de facturar las returns
            invoices = rec.env['account.invoice'].browse(
                self.action_invoice_create(final=True))
            if invoices and \
                    rec.type_id.invoicing_atomation == 'validate_invoice':
                invoices.signal_workflow('invoice_open')

    @api.multi
    def run_picking_atomation(self):
        packs_to_unlink = self.env['stock.pack.operation']
        for rec in self.filtered(lambda x: x.type_id.picking_atomation \
                != 'none' and x.procurement_group_id):
            # we add invalidate because on boggio we have add an option
            # for tracking_disable and with that setup pickings where not seen 
            rec.invalidate_cache()
            pickings = rec.picking_ids
            if rec.type_id.book_id:
                pickings.update({'book_id': rec.type_id.book_id.id})
            if rec.type_id.picking_atomation == 'validate':
                pickings.force_assign()
            elif rec.type_id.picking_atomation == 'validate_no_force':
                pickings.action_assign()
                products = []
                for move in pickings.mapped('move_lines'):
                    if move.state != 'assigned':
                        products.append(move.product_id)
                if products:
                    raise ValidationError(_(
                        'Products:\n%s\nAre not available, we suggest use'
                        ' another type of sale to generate a'
                        ' partial delivery.'
                    ) % ('\n'.join(x.name for x in products)))
            for pack in pickings.mapped('pack_operation_ids'):
                if pack.product_qty > 0:
                    pack.update({'qty_done': pack.product_qty})
                else:
                    packs_to_unlink |= pack
            # because of ensure_one on delivery module
            for pick in pickings:
                pick.do_transfer()
        packs_to_unlink.unlink()

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        self.run_picking_atomation()
        self.run_invoicing_atomation()
        return res

    @api.multi
    def _prepare_invoice(self):
        if self.type_id.journal_id:
            self = self.with_context(
                force_company=self.type_id.journal_id.company_id.id)
        res = super(SaleOrder, self)._prepare_invoice()
        if self.type_id.payment_atomation and self.type_id.payment_journal_id:
            res['pay_now_journal_id'] = self.type_id.payment_journal_id.id
        return res
