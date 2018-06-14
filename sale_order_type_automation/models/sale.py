##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
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
            if invoices:
                if rec.type_id.invoicing_atomation == 'validate_invoice':
                    invoices.action_invoice_open()
                elif rec.type_id.invoicing_atomation == 'try_validate_invoice':
                    # TODO en v11 no haria falta el savepoint porque al no usar
                    # workflow la factura deberia igual hacer el rollback
                    # TODO we should improve this because if more than one
                    # invoice is created and just one invoice has the error,
                    # all of them are rolled back, perhaps a new cursor can
                    # help on this
                    try:
                        self.env.cr.execute('SAVEPOINT try_validate_invoice')
                        invoices.action_invoice_open()
                        self.env.cr.execute(
                            'RELEASE SAVEPOINT try_validate_invoice')
                    except Exception, e:
                        self.env.cr.execute(
                            'ROLLBACK TO SAVEPOINT try_validate_invoice')
                        message = _(
                            "We couldn't validate the automatically created "
                            "invoices (ids %s), you will need to validate them"
                            " manually. This is what we get: %s") % (
                                invoices.ids, e)
                        invoices.message_post(message)
                        rec.message_post(message)

    @api.multi
    def run_picking_atomation(self):
        packs_to_unlink = self.env['stock.pack.operation']
        is_jit_installed = self.env['ir.module.module'].search(
            [('name', '=', 'procurement_jit'),
             ('state', '=', 'installed')], limit=1)
        for rec in self.filtered(lambda x: x.type_id.picking_atomation
                                 != 'none' and x.procurement_group_id):
            # we add invalidate because on boggio we have add an option
            # for tracking_disable and with that setup pickings where not seen
            rec.invalidate_cache()
            pickings = rec.picking_ids
            if not is_jit_installed:
                pickings.action_assign()
            if rec.type_id.book_id:
                pickings.update({'book_id': rec.type_id.book_id.id})
            if rec.type_id.picking_atomation == 'validate':
                pickings.force_assign()
            elif rec.type_id.picking_atomation == 'validate_no_force':
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
        # we use this because compatibility with sale exception module
        if isinstance(res, bool) and res:
            self.run_picking_atomation()
            self.run_invoicing_atomation()
            if self.type_id.set_done_on_confirmation:
                self.action_done()
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


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    @api.multi
    def _create_invoice(self, order, so_line, amount):
        if order.type_id.journal_id:
            self = self.with_context(
                default_sale_type_id=order.type_id.id,
                default_journal_id=order.type_id.journal_id.id,
            )
            invoice = super(SaleAdvancePaymentInv, self)._create_invoice(
                order=order, so_line=so_line, amount=amount)
        return invoice
