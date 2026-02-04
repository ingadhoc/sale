##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleAdvancePaymentInvWizard(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    advance_payment_method = fields.Selection(
        selection_add=[
            ("invoice_gathering_zero", "Factura en cero descontando acopio"),
        ],
        ondelete={"invoice_gathering_zero": "cascade"},
    )

    def create_invoices(self):
        sale_orders = self.env["sale.order"].browse(self.env.context.get("active_ids", []))
        if self.advance_payment_method == "invoice_gathering_zero":
            invoices = sale_orders.with_context(invoice_gathering=True)._create_invoices()
            return self.sale_order_ids.action_view_invoice(invoices=invoices)
        else:
            uninvoiced_gathering_orders = sale_orders.filtered(
                lambda so: so.is_gathering and not so.has_gathering_invoice
            )
            res = False
            if uninvoiced_gathering_orders:
                res = super(
                    SaleAdvancePaymentInvWizard,
                    self.with_context(active_ids=uninvoiced_gathering_orders.ids, first_gathering_invoice=True),
                ).create_invoices()
            remaining_orders = sale_orders - uninvoiced_gathering_orders
            if remaining_orders:
                res = super(
                    SaleAdvancePaymentInvWizard,
                    self.with_context(
                        active_ids=remaining_orders.ids,
                    ),
                ).create_invoices()
            return res

    # TODO seria ideal esto llevarlo a UX y que no se muestre la opción directamente
    @api.constrains("advance_payment_method")
    def _check_payment_method(self):
        if self.advance_payment_method == "invoice_gathering_zero":
            sale_orders = self.env["sale.order"].browse(self.env.context.get("active_ids", []))
            invalid_orders = sale_orders.filtered(lambda so: not so.is_gathering)
            if invalid_orders:
                raise ValidationError(
                    _("The 'Factura en cero descontando acopio' method can only be used for gathering sales.")
                )

    def _create_invoices(self, sale_orders):
        invoice = super()._create_invoices(sale_orders)
        if invoice.invoice_line_ids.filtered("is_downpayment"):
            invoice.write({"ref": "Acopio"})
        return invoice
