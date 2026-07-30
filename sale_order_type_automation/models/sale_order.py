##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging

from odoo import _, fields, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools.safe_eval import (
    datetime as safe_eval_datetime,
    dateutil as safe_eval_dateutil,
    safe_eval,
)

_logger = logging.getLogger(__name__)


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
            # Check sale order exclusion domain: create invoice but skip validation
            eval_ctx = {
                "datetime": safe_eval_datetime,
                "context_today": lambda: fields.Date.context_today(rec),
                "relativedelta": safe_eval_dateutil.relativedelta.relativedelta,
            }
            skip_validation = False
            if rec.type_id.sale_order_filter_domain:
                so_domain = safe_eval(
                    rec.type_id.sale_order_filter_domain,
                    eval_ctx,
                )
                if so_domain and rec.filtered_domain(so_domain):
                    skip_validation = True
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
            if (
                rec.type_id.invoicing_atomation == "validate_invoice"
                and not rec.type_id.background_post
                and not skip_validation
            ):
                if rec.env.context.get("commit_invoice_automation"):
                    rec.env.cr.commit()
                if rec.type_id.invoice_validate_domain:
                    domain = safe_eval(
                        rec.type_id.invoice_validate_domain,
                        eval_ctx,
                    )
                    invoices_not_validated = invoices.filtered_domain(domain) if domain else rec.env["account.move"]
                    invoices_to_validate = invoices - invoices_not_validated
                else:
                    invoices_to_validate = invoices
                    invoices_not_validated = rec.env["account.move"]
                if not invoices_to_validate:
                    continue
                if rec.env.context.get("background_post_defer"):
                    invoices_to_validate = invoices_to_validate.with_context(force_background_post=True)
                try:
                    invoices_to_validate.sudo().action_post()
                except Exception as error:
                    rec._handle_invoicing_automation_error(invoices, error)
                else:
                    rec._log_background_post_defer(invoices_to_validate)
                # Post message for invoices that were not validated due to domain filter
                if invoices_not_validated:
                    domain_message = _(
                        "⚠️Esta factura no se validó porque no cumplió la condición del tipo de pedido de venta "
                        "para que sea validada automáticamente. Revisar la FA/OV si tiene que hacer alguna "
                        "modificación y luego validarla manualmente."
                    )
                    invoices_not_validated._message_log_batch(
                        bodies=dict((invoice.id, domain_message) for invoice in invoices_not_validated)
                    )
            elif skip_validation and invoices:
                # Post message for invoices not validated due to sale order domain filter
                skip_message = _(
                    "⚠️Esta factura no se validó porque no cumplió la condición del tipo de pedido de venta "
                    "para que sea validada automáticamente. Revisar la FA/OV si tiene que hacer alguna "
                    "modificación y luego validarla manualmente."
                )
                invoices._message_log_batch(bodies=dict((invoice.id, skip_message) for invoice in invoices))

    def _log_background_post_defer(self, invoices):
        self.ensure_one()
        if not self.env.context.get("background_post_defer"):
            return
        invoices = invoices.filtered(lambda x: x.state == "draft")
        if not invoices:
            return
        if self.env.context.get("background_post_batch_defer"):
            reason = self.env._(
                "more than %s transfers were validated at once",
                self.env["account.move"]._get_background_post_batch_size(),
            )
        else:
            reason = self.env._("its validation failed and the operation was run again anyway")
        self._message_log(
            body=self.env._("The invoice was left in draft to be validated by the background post process, %s.", reason)
        )
        invoices._message_log_batch(
            bodies=dict.fromkeys(
                invoices.ids,
                self.env._(
                    "This invoice was left in draft to be validated by the background post process, "
                    "%(reason)s. The error, if there was one, is logged on %(order)s.",
                    reason=reason,
                    order=self._get_html_link(),
                ),
            )
        )

    def _get_invoicing_automation_error_body(self, invoices, error):
        self.ensure_one()
        return self.env._(
            "We couldn't validate the automatically created "
            "invoices (ids %s), you will need to validate them"
            " manually. This is what we get: %s"
        ) % (invoices.ids, error)

    def _get_internal_message_partners(self):
        return self.message_partner_ids.filtered(lambda x: x.user_ids and all(u._is_internal() for u in x.user_ids))

    def _log_invoicing_automation_error(self, invoices, error, xml_id=False):
        self.ensure_one()
        message, action_id = str(error), False
        try:
            with self.pool.cursor() as new_cr:
                # the current transaction holds the order row, so a lock on it would hang here
                new_cr.execute("SET LOCAL lock_timeout = '5s'")
                order = self.with_env(self.env(cr=new_cr))
                message = order._get_invoicing_automation_error_body(invoices, error)
                if xml_id:
                    action_id = order.env.ref(xml_id).id
                if order.exists():
                    order.message_post(body=message, partner_ids=order._get_internal_message_partners().ids)
        except Exception:
            _logger.exception("Could not log the invoicing automation error on sale order %s", self.id)
        return message, action_id

    def _handle_invoicing_automation_error(self, invoices, error):
        self.ensure_one()
        if (
            self.env.context.get("background_post_defer")
            or self.env.context.get("force_background_post")
            or self.env.context.get("commit_invoice_automation")
        ):
            message = self._get_invoicing_automation_error_body(invoices, error)
            invoices._message_log_batch(bodies=dict((invoice.id, message) for invoice in invoices))
            self.message_post(body=message)
            return

        deferrable = self.env["account.move"]._background_post_available()
        picking_ids = self.env.context.get("background_post_picking_ids")
        if picking_ids:
            xml_id = "sale_order_type_automation.action_picking_validate_force_background_post"
            button_text = self.env._("Validate anyway")
            hint = self.env._(
                "You can validate the transfer anyway. The invoice will be created and validated "
                "later on by the background post process."
            )
            context = {"active_model": "stock.picking", "active_ids": picking_ids, "active_id": picking_ids[0]}
        else:
            xml_id = "sale_order_type_automation.action_sale_order_confirm_force_background_post"
            button_text = self.env._("Confirm anyway")
            hint = self.env._(
                "You can confirm the order anyway. The invoice will be created and validated later "
                "on by the background post process."
            )
            context = {"active_model": "sale.order", "active_ids": self.ids, "active_id": self.id}

        message, action_id = self._log_invoicing_automation_error(invoices, error, deferrable and xml_id)
        if not action_id:
            raise UserError(message) from error
        raise RedirectWarning(message + "\n\n" + hint, action_id, button_text, context) from error

    def action_confirm_force_background_post(self):
        self.with_context(background_post_defer=True).action_confirm()
        return self._get_records_action()

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
        for rec in self.filtered(lambda x: x.type_id.picking_atomation != "none" and x.picking_ids):
            rec._process_pickings()
        return True

    def _process_pickings(self, prev_pending=None):
        self.ensure_one()
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
            pick.with_context(background_post_confirming_order=True).button_validate()
            pending_after = self.picking_ids.filtered(lambda x: x.state not in ("done", "cancel"))
            if pending_after:
                pending_after.action_assign()
        pending_final = self.picking_ids.filtered(lambda x: x.state not in ("done", "cancel"))
        if pending_final and pending_final != (prev_pending or set()):
            self._process_pickings(prev_pending=pending_final)

    def action_confirm(self):
        res = super().action_confirm()
        # we use this because compatibility with sale exception module
        if not (isinstance(res, dict) and res.get("xml_id") == "sale_exception.action_sale_exception_confirm"):
            # because it's needed to return actions if exists
            picking_action = self.run_picking_automation()
            self.sudo().run_invoicing_atomation()
            if self.type_id.set_done_on_confirmation:
                self.action_lock()
            if isinstance(picking_action, dict) and isinstance(res, dict) and res.get("type") == "ir.actions.client":
                params = dict(res.get("params") or {})
                params["next"] = picking_action
                res["params"] = params
            elif isinstance(picking_action, dict) and not res:
                res = picking_action
        return res
