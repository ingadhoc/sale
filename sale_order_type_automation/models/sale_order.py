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
                    invoices_to_validate = (invoices - invoices.filtered_domain(domain)) if domain else invoices
                else:
                    invoices_to_validate = invoices
                if not invoices_to_validate:
                    continue
                try:
                    invoices_to_validate.sudo().action_post()
                except Exception as error:
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
            pick.button_validate()
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
