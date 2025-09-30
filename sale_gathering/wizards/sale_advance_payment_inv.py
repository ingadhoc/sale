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
        sale_orders = self.env["sale.order"].browse(self._context.get("active_ids", []))
        if self.advance_payment_method == "invoice_gathering_zero":
            invoices = sale_orders.with_context(invoice_gathering=True)._create_invoices()
            return self.sale_order_ids.action_view_invoice(invoices=invoices)
        else:
            return super().create_invoices()

    # TODO seria ideal esto llevarlo a UX y que no se muestre la opción directamente
    @api.constrains("advance_payment_method")
    def _check_payment_method(self):
        if self.advance_payment_method == "invoice_gathering_zero":
            sale_orders = self.env["sale.order"].browse(self._context.get("active_ids", []))
            invalid_orders = sale_orders.filtered(lambda so: not so.is_gathering)
            if invalid_orders:
                raise ValidationError(
                    _("The 'Factura en cero descontando acopio' method can only be used for gathering sales.")
                )
