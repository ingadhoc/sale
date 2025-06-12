##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _prepare_invoice_values(self, order, so_line):
        """
        Forzamos compania de diario de sale type
        """
        if not order.type_id.journal_id:
            return super()._prepare_invoice_values(order, so_line)
        company = order.type_id.journal_id.company_id
        self = self.with_company(company.id)
        res = super()._prepare_invoice_values(order, so_line)
        if company.id != order.company_id.id:
            taxes = self.product_id.taxes_id.filtered(
                lambda r: not order.company_id or r.company_id == company)
            if order.fiscal_position_id and taxes:
                tax_ids = order.fiscal_position_id.map_tax(taxes).ids
            else:
                tax_ids = taxes.ids
            res['invoice_line_ids'][0][2]['tax_ids'] = [(6, 0, tax_ids)]

        return res

    def _prepare_down_payment_product_values(self):
        res = super()._prepare_down_payment_product_values()
        if res['company_id']:
            res['company_id'] = False
        return res

    def _create_invoices(self, sale_orders):
        # if discount product has a company associated, we need to remove it before changing the company in invoice
        if self.mapped('sale_order_ids.type_id.journal_id.company_id') != self.mapped('sale_order_ids.company_id'):
            discount_lines = self.mapped('sale_order_ids.order_line').filtered(
                lambda x: x.product_id == self.company_id.sale_discount_product_id
            )
            if discount_lines and discount_lines.product_id.company_id:
                discount_lines[0].product_id.write({'company_id': False})

        return super(SaleAdvancePaymentInv, self)._create_invoices(sale_orders=sale_orders)
