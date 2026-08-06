##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import (
    datetime as safe_eval_datetime,
    dateutil as safe_eval_dateutil,
    safe_eval,
)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def run_invoicing_atomation(self):
        for rec in self.filtered(
            lambda x: (
                x.type_id
                and x.type_id.invoicing_atomation != "none"
                and x.invoice_status == "to invoice"
                and any(line.qty_to_invoice for line in x.order_line)
            )
        ):
            # we take into account if there are any transaction finish from the e-commerce
            #  and not continue with the automation in this case
            if (
                rec.transaction_ids
                and rec.env["ir.config_parameter"].sudo().get_param("sale.automatic_invoice")
                and any([True if transaction.state == "done" else False for transaction in rec.transaction_ids])
            ):
                continue
            # a list is returned but only one invoice should be returned
            # usamos final para que reste adelantos y tmb por ej
            # por si se usa el modulo de facturar las returns
            if rec.type_id.background_post:
                rec = rec.with_context(default_background_post=True)
            invoices = rec._create_invoices(final=True)
            if not invoices:
                continue

            if rec.type_id.invoicing_atomation == "validate_invoice" and not rec.type_id.background_post:
                if rec._context.get("commit_invoice_automation"):
                    rec.env.cr.commit()
                try:
                    if rec.type_id.invoice_validate_domain:
                        domain = safe_eval(
                            rec.type_id.invoice_validate_domain,
                            {
                                "datetime": safe_eval_datetime,
                                "context_today": lambda: fields.Date.context_today(rec),
                                "relativedelta": safe_eval_dateutil.relativedelta.relativedelta,
                            },
                        )
                        invoices_to_validate = invoices.filtered_domain(domain)
                        # Post message on invoices that don't meet the validation criteria
                        invoices_not_validated = invoices - invoices_to_validate
                        if invoices_not_validated:
                            message = _(
                                "⚠️Esta factura no se valido porque no cumplio la condicion del tipo de pedido de "
                                "venta para que sea validad automaticamente. Revisar la FA/OV si tiene que hacer "
                                "alguna modificacion y luego validarla manualmente."
                            )
                            for invoice in invoices_not_validated:
                                invoice.message_post(body=message)
                    else:
                        invoices_to_validate = invoices
                    invoices_to_validate.with_context(sale_type_id=rec.type_id.id).sudo().action_post()
                    for invoice in invoices_to_validate:  # to avoid "expected singleton" error
                        if (
                            invoice.name
                            and not invoice.line_ids.mapped("move_name")
                            and invoice.name not in invoice.line_ids.mapped("move_name")
                        ):
                            invoice.env.add_to_compute(invoice.line_ids._fields["move_name"], invoice.line_ids)
                except Exception as error:
                    rec.env.cr.rollback()
                    if not rec._context.get("commit_invoice_automation"):
                        raise error
                    message = _(
                        "We couldn't validate the automatically created "
                        "invoices (ids %s), you will need to validate them"
                        " manually. This is what we get: %s"
                    ) % (invoices.ids, error)
                    invoices.message_post(body=message)
                    rec.message_post(body=message)

    def run_picking_automation(self):
        # If there products are the type 'service' equals the
        #  delivered qyt to order qty for this sale order line
        for order_line in self.mapped("order_line").filtered(
            lambda x: (
                x.order_id.type_id.picking_atomation != "none"
                and x.product_id.type == "service"
                and x.product_id.service_type == "manual"
                and x.product_id.expense_policy == "no"
            )
        ):
            order_line.qty_delivered = order_line.product_uom_qty
        print_actions = []
        for rec in self.filtered(lambda x: x.type_id.picking_atomation != "none" and x.procurement_group_id):
            # ``or []`` porque _process_pickings puede estar extendido y no devolver nada:
            # que no imprima es tolerable, que no se pueda confirmar la venta no.
            print_actions += rec._process_pickings() or []
        return self._merge_picking_print_actions(print_actions) or True

    def _merge_picking_print_actions(self, actions):
        """Junta los reportes a imprimir en una sola acción ``do_multi_print``.

        Lo que no sea un reporte se descarta a propósito: ``button_validate`` puede
        devolver un asistente (backorder, por ejemplo) y acá no hay cliente que lo
        ejecute, igual que antes de propagar nada."""
        reports = []
        for action in actions:
            if not isinstance(action, dict):
                continue
            if action.get("tag") == "do_multi_print":
                reports += (action.get("params") or {}).get("reports") or []
            elif action.get("type") == "ir.actions.report":
                reports.append(action)
        if not reports:
            return False
        return {
            "type": "ir.actions.client",
            "tag": "do_multi_print",
            "params": {"reports": reports},
        }

    def _process_pickings(self, prev_pending=None):
        self.ensure_one()
        print_actions = []
        pickings = self.picking_ids.filtered(lambda x: x.state not in ("done", "cancel"))
        for pick in pickings.sorted(lambda p: p.picking_type_id.sequence):
            pick.action_assign()
            if self.type_id.picking_atomation == "validate":
                pick.new_force_availability()
            elif self.type_id.picking_atomation == "validate_no_force":
                products = [move.product_id for move in pick.move_ids if move.state != "assigned"]
                if products:
                    raise UserError(
                        _(
                            "The following products are not available, we "
                            "suggest to check stock or to use a sale type that "
                            "forces availability.\nProducts:\n* %s\n"
                        )
                        % "\n* ".join(x.name for x in products)
                    )
                for op in pick.move_line_ids:
                    op.with_context(sale_automation=True).quantity = op.quantity_product_uom
            # Validamos server-side: si descartamos la acción de impresión que
            # devuelve button_validate, nadie la ejecuta y no se imprime nada.
            print_actions.append(pick.button_validate())
            pending_after = self.picking_ids.filtered(lambda x: x.state not in ("done", "cancel"))
            if pending_after:
                pending_after.action_assign()
        pending_final = self.picking_ids.filtered(lambda x: x.state not in ("done", "cancel"))
        if pending_final and pending_final != (prev_pending or set()):
            print_actions += self._process_pickings(prev_pending=pending_final) or []
        return print_actions

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
        if (self.type_id.payment_atomation != "none") and self.type_id.payment_journal_id:
            res["pay_now_journal_id"] = self.type_id.payment_journal_id.id
        if self.type_id:
            res["sale_type_id"] = self.type_id.id
        return res
