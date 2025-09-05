##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, models
from odoo.fields import Command


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def run_invoicing_atomation(self):
        gathering_lines = self.filtered("is_gathering")
        super(SaleOrder, gathering_lines.with_context(invoice_gathering=True)).run_invoicing_atomation()
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
            lambda o: o.is_gathering
            and o.type_id
            and (o.type_id.invoicing_atomation != "none" or o.type_id.picking_atomation != "none")
        )
        if orders_to_automate and self._has_quantity_changes(values):
            orders_picking_automation = orders_to_automate.filtered(lambda o: o.type_id.picking_atomation != "none")
            orders_picking_automation.run_picking_automation()
            (orders_to_automate - orders_picking_automation).run_invoicing_atomation()

        return res

    def action_confirm(self):
        res = super().action_confirm()
        if isinstance(res, bool) and res:
            for order in self.filtered(
                lambda x: x.is_gathering and x.type_id.invoicing_atomation != "none" and not x.has_gathering_invoice
            ):
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
                invoices = advance_payment_wizard.with_context(advance_payment=True)._create_invoices(order)
                if invoices and order.type_id.invoicing_atomation == "validate_invoice":
                    try:
                        invoices.sudo().action_post()
                    except Exception as error:
                        message = _(
                            "We couldn't validate the automatically created "
                            "gathering invoice (ids %s), you will need to validate them"
                            " manually. This is what we get: %s"
                        ) % (invoices.ids, error)
                        invoices.message_post(body=message)
                        order.message_post(body=message)
        return res
