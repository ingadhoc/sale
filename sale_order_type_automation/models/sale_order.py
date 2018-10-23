##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def run_invoicing_atomation(self):
        invoice = self.env['account.invoice']
        for rec in self.filtered(
                lambda x: x.type_id.invoicing_atomation and
                x.type_id.invoicing_atomation != 'none'):
            # we add this check just because if we call
            # action_invoice_create and nothing to invoice, it raise
            # an error
            if not any(
                    line.qty_to_invoice for line in rec.order_line):
                _logger.warning('Noting to invoice')
                continue

            # a list is returned but only one invoice should be returned
            # usamos final para que reste adelantos y tmb por ej
            # por si se usa el modulo de facturar las returns
            invoices = invoice.browse(self.action_invoice_create(final=True))
            if not invoices:
                continue

            if rec.type_id.invoicing_atomation == 'validate_invoice':
                invoices.action_invoice_open()
            elif rec.type_id.invoicing_atomation == 'try_validate_invoice':
                try:
                    invoices.action_invoice_open()
                except Exception as error:
                    message = _(
                        "We couldn't validate the automatically created "
                        "invoices (ids %s), you will need to validate them"
                        " manually. This is what we get: %s") % (
                            invoices.ids, error)
                    invoices.message_post(message)
                    rec.message_post(message)

    @api.multi
    def run_picking_atomation(self):
        for rec in self.filtered(
                lambda x: x.type_id.picking_atomation != 'none' and
                x.procurement_group_id):
            # we add invalidate because on boggio we have add an option
            # for tracking_disable and with that setup pickings where not seen
            rec.invalidate_cache()
            pickings = rec.picking_ids
            if rec.type_id.book_id:
                pickings.update({'book_id': rec.type_id.book_id.id})
            if rec.type_id.picking_atomation == 'validate':
                # this method already call action_assign
                pickings.new_force_availability()
            elif rec.type_id.picking_atomation == 'validate_no_force':
                if not self.env['ir.module.module'].search([
                        ('name', '=', 'procurement_jit'),
                        ('state', '=', 'installed')], limit=1):
                    pickings.action_assign()
                products = []
                for move in pickings.mapped('move_lines'):
                    if move.state != 'assigned':
                        products.append(move.product_id)
                if products:
                    raise UserError(_(
                        'The following products are not available, we suggest '
                        'to check stock or to use a sale type that force '
                        'availability.\nProducts:\n* %s\n '
                    ) % ('\n *'.join(x.name for x in products)))
                for op in pickings.mapped('move_line_ids'):
                    op.qty_done = op.product_uom_qty
            # because of ensure_one on delivery module
            for pick in pickings:
                pick.action_done()

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
