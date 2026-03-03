##############################################################################
from odoo import models


class SaleAdvancePaymentInvWizard(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _create_invoices(self, sale_orders):
        invoice = super()._create_invoices(sale_orders)

        if self.advance_payment_method == "fixed" and sale_orders.filtered("is_gathering"):
            for order in sale_orders.filtered("is_gathering"):
                delivery_lines = order.order_line.filtered(lambda l: l.is_delivery and l.product_uom_qty > 0)
                if delivery_lines:
                    for line in delivery_lines:
                        line_vals = line._prepare_invoice_line(quantity=line.product_uom_qty)
                        line_vals["move_id"] = invoice.id
                        self.env["account.move.line"].create(line_vals)

        return invoice
