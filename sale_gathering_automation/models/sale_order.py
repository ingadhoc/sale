##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, fields, models
from odoo.fields import Command
from odoo.tools.safe_eval import (
    datetime as safe_eval_datetime,
    dateutil as safe_eval_dateutil,
    safe_eval,
)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_create_invoice_with_automation(self):
        self.ensure_one()
        if (
            self.is_gathering
            and self.state == "sale"
            and self.type_id
            and self.type_id.invoicing_atomation != "none"
            and self.has_gathering_invoice
            and any(line.qty_to_invoice for line in self.order_line)
        ):
            self.run_invoicing_atomation()
            return self.action_view_invoice()

        return self.env.ref("sale.action_view_sale_advance_payment_inv").sudo().read()[0]

    def run_invoicing_atomation(self):
        gathering_lines = self.filtered("is_gathering")
        # Solo ejecutar el flujo de gathering para órdenes que YA tienen factura de acopio.
        # Si no tienen factura de acopio, action_confirm se encarga de crearla.
        # Esto evita que se creen 2 facturas al confirmar.
        gathering_with_invoice = gathering_lines.filtered("has_gathering_invoice")
        super(SaleOrder, gathering_with_invoice.with_context(invoice_gathering=True)).run_invoicing_atomation()
        super(SaleOrder, self - gathering_lines).run_invoicing_atomation()

    def _has_quantity_changes(self, values):
        if "order_line" not in values:
            return False

        for command in values["order_line"]:
            if not isinstance(command, (list, tuple)) or len(command) != 3:
                continue

            cmd_type, _, cmd_values = command
            if cmd_type == Command.CREATE and isinstance(cmd_values, dict):
                if "product_uom_qty" in cmd_values:
                    return True

            elif cmd_type == Command.UPDATE and isinstance(cmd_values, dict):
                if "product_uom_qty" in cmd_values:
                    return True

        return False

    def write(self, values):
        res = super().write(values)
        orders_to_automate = self.filtered(
            lambda o: o.is_gathering and o.type_id and o.type_id.picking_atomation != "none"
        )
        if orders_to_automate and self._has_quantity_changes(values):
            orders_picking_automation = orders_to_automate.filtered(lambda o: o.type_id.picking_atomation != "none")
            orders_picking_automation.run_picking_automation()
            # no corremos la automatización de facturacion porque en gathering nos parece muy invasivo, guardar termina
            # facturando automáticammente. Además deberíamos arreglar que no facture el gathering ni bien
            # se confirma la venta. La idea es recomendar que para gathering con factura automática se use segun entrega
            # (orders_to_automate - orders_picking_automation).run_invoicing_atomation()

        return res

    def action_confirm(self):
        res = super().action_confirm()
<<<<<<< 8e8b6f0db17248b0a42067b21acabdf75efbf73a
        if isinstance(res, bool) and res:
            for order in self.filtered(
                lambda x: x.is_gathering
                and x.type_id
                and x.type_id.invoicing_atomation != "none"
                and not x.has_gathering_invoice
            ):
||||||| 2eda38dc6b5fe2268a9aacb7765a03c97047a64a
        if isinstance(res, bool) and res:
            for order in self.filtered(
                lambda x: x.is_gathering and x.type_id.invoicing_atomation != "none" and not x.has_gathering_invoice
            ):
=======
        # res puede ser una acción y no solo True: lo que define si facturamos es el estado del pedido
        orders_to_invoice = self.filtered(
            lambda x: x.state == "sale"
            and x.is_gathering
            and x.type_id.invoicing_atomation != "none"
            and not x.has_gathering_invoice
        )
        if orders_to_invoice:
            for order in orders_to_invoice:
>>>>>>> 7ad65cf29ce0be2fbcb809ddf72b59becf0b2843
                advance_payment_wizard = (
                    self.env["sale.advance.payment.inv"]
                    .with_context()
                    .create(
                        {
                            "advance_payment_method": "fixed",
                            "sale_order_ids": order.ids,
                            "fixed_amount": order.gathering_amount_with_taxes,
                        }
                    )
                )
                advance_payment_wizard._check_amount_is_positive()
                invoices = advance_payment_wizard.with_context(first_gathering_invoice=True)._create_invoices(order)
                if invoices and order.type_id.invoicing_atomation == "validate_invoice":
                    try:
                        if order.type_id.invoice_validate_domain:
                            domain = safe_eval(
                                order.type_id.invoice_validate_domain,
                                {
                                    "datetime": safe_eval_datetime,
                                    "context_today": lambda: fields.Date.context_today(order),
                                    "relativedelta": safe_eval_dateutil.relativedelta.relativedelta,
                                },
                            )
                            invoices_to_validate = invoices - invoices.filtered_domain(domain)
                        else:
                            invoices_to_validate = invoices
                        invoices_to_validate.sudo().action_post()
                    except Exception as error:
                        message = _(
                            "We couldn't validate the automatically created "
                            "gathering invoice (ids %s), you will need to validate them"
                            " manually. This is what we get: %s"
                        ) % (invoices.ids, error)
                        invoices.message_post(body=message)
                        order.message_post(body=message)
        return res
