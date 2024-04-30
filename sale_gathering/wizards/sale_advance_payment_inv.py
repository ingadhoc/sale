##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class SaleAdvancePaymentInvWizard(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    advance_payment_method = fields.Selection(selection_add=[
        ('invoice_gathering_zero', 'Factura en cero descontando acopio'),],
        ondelete={'invoice_gathering_zero': 'cascade'},
    )


    def _prepare_so_line(self, order, analytic_tag_ids, tax_ids, amount):
        result = super()._prepare_so_line(order, analytic_tag_ids, tax_ids, amount)
        result['sequence'] = 0
        return result


    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
        if self.advance_payment_method == 'invoice_gathering_zero':
            invoices = sale_orders.with_context(invoice_gathering=True)._create_invoices(final=True)
        else:
            self = self.with_context(advance_payment=True)
            return super().create_invoices()
        return self.sale_order_ids.action_view_invoice(invoices=invoices)
