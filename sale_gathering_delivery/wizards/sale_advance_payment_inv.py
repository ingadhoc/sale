##############################################################################
from odoo import models


class SaleAdvancePaymentInvWizard(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _create_invoices(self, sale_orders):
        invoice = super()._create_invoices(sale_orders)

        if self.advance_payment_method == "fixed" and sale_orders.filtered("is_gathering"):
            created_lines = self.env["account.move.line"]
            for order in sale_orders.filtered("is_gathering"):
                delivery_lines = order.order_line.filtered(lambda l: l.is_delivery and l.product_uom_qty > 0)
<<<<<<< d9857ba0b3c323b3a2d6ab448921edcea82aaa45
                if delivery_lines:
                    for line in delivery_lines:
                        line_vals = line._prepare_invoice_line(quantity=line.product_uom_qty)
                        line_vals["move_id"] = invoice.id
                        self.env["account.move.line"].create(line_vals)
||||||| 9b276ee7b2752b6d8e66a06fef469f4a0e2195c6
                if delivery_lines:
                    for line in delivery_lines:
                        line_vals = self._prepare_gathering_delivery_invoice_line_vals(line, invoice)
                        self.env["account.move.line"].with_company(invoice.company_id).create(line_vals)
=======
                for line in delivery_lines:
                    line_vals = self._prepare_gathering_delivery_invoice_line_vals(line, invoice)
                    created_lines |= self.env["account.move.line"].with_company(invoice.company_id).create(line_vals)

            # Strip any incompatible taxes injected by the compute during create,
            # inside _sync_dynamic_lines so _sync_tax_lines regenerates the
            # tax accounting entries correctly.
            if created_lines:
                container = {"records": invoice}
                with invoice._sync_dynamic_lines(container):
                    created_lines._strip_gathering_incompatible_taxes()
>>>>>>> 749a49859c985c7bf3a8994d3df4917777284027

        return invoice
