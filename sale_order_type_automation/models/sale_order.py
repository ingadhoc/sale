##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def run_invoicing_atomation(self):
        for rec in self.filtered(
            lambda x: (
                x.type_id.invoicing_atomation != 'none' and
                any(line.qty_to_invoice for line in x.order_line)
            )
        ):
            # we take into account if there are any transaction finish from the e-commerce
            #  and not continue with the automation in this case
            if self.transaction_ids and self.env['ir.config_parameter'].sudo().get_param('sale.automatic_invoice')\
                and any(
                    [True if transaction.state == 'done' else False for transaction in self.transaction_ids]):
                continue
            # a list is returned but only one invoice should be returned
            # usamos final para que reste adelantos y tmb por ej
            # por si se usa el modulo de facturar las returns
            invoices = self._create_invoices(final=True)
            if not invoices:
                continue
            if rec.type_id.invoicing_atomation == 'validate_invoice':
                if self._context.get("commit_invoice_automation"):
                    rec.env.cr.commit()
                try:
                    invoices.sudo().action_post()
                except Exception as error:
                    rec.env.cr.rollback()
                    if not self._context.get("commit_invoice_automation"):
                        raise error
                    message = _(
                        "We couldn't validate the automatically created "
                        "invoices (ids %s), you will need to validate them"
                        " manually. This is what we get: %s") % (
                            invoices.ids, error)
                    invoices.message_post(body=message)
                    rec.message_post(body=message)

    def run_picking_automation(self):
        # If there products are the type 'service' equals the
        #  delivered qyt to order qty for this sale order line
        for order_line in self.mapped('order_line').filtered(
            lambda x: x.order_id.type_id.picking_atomation != 'none'
            and x.product_id.type == 'service'
            and x.product_id.service_type == 'manual'
            and x.product_id.expense_policy == 'no'
        ):
            order_line.qty_delivered = order_line.product_uom_qty
        for rec in self.filtered(
            lambda x: x.type_id.picking_atomation != 'none'
            and x.procurement_group_id
        ):
            pickings = rec.picking_ids.filtered(
                lambda x: x.state not in ('done', 'cancel')
            )
            pickings.action_assign()
            pickings = pickings.sorted(
                key=lambda x: (x.state != 'assigned', x.id)
            )
            self._process_pickings(pickings, rec)
        return True

    def _process_pickings(self, pickings, rec):
        products = []
        for pick in pickings:
            if rec.type_id.picking_atomation == 'validate':
                pick.new_force_availability()
            elif rec.type_id.picking_atomation == 'validate_no_force':
                products.extend(
                    move.product_id for move in pick.move_ids if move.state != 'assigned'
                )
                if products:
                    raise UserError(_(
                        'The following products are not available, we '
                        'suggest to check stock or to use a sale type that'
                        'force availability.\nProducts:\n* %s\n'
                    ) % '\n* '.join(x.name for x in products))

                for op in pick.move_line_ids:
                    op.quantity = op.quantity_product_uom

            pick.button_validate()

    def action_confirm(self):
        res = super().action_confirm()
        # we use this because compatibility with sale exception module
        if isinstance(res, bool) and res:
            # because it's needed to return actions if exists
            res = self.run_picking_automation()
            self.sudo().run_invoicing_atomation()
            if self.type_id.set_done_on_confirmation:
                self.action_lock()
        return res

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        if (self.type_id.payment_atomation != 'none') and self.type_id.payment_journal_id:
            res['pay_now_journal_id'] = self.type_id.payment_journal_id.id
        return res
