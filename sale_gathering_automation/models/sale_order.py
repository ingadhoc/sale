##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def run_invoicing_atomation(self):
        gathering_lines = self.filtered("is_gathering")
        super(SaleOrder, gathering_lines.with_context(invoice_gathering=True)).run_invoicing_atomation()
        super(SaleOrder, self - gathering_lines).run_invoicing_atomation()

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
