##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _prepare_invoice_values(self, order, name, amount, so_line):
        """
        Forzamos compania de diario de sale type
        """
        if not order.type_id.journal_id:
            return super()._prepare_invoice_values(order, name, amount, so_line)
        company = order.type_id.journal_id.company_id
        self = self.with_context(force_company=company.id)
        res = super()._prepare_invoice_values(order, name, amount, so_line)
        if company != order.company_id.id:
            taxes = self.product_id.taxes_id.filtered(
                lambda r: not order.company_id or r.company_id == company)
            if order.fiscal_position_id and taxes:
                tax_ids = order.fiscal_position_id.map_tax(taxes).ids
            else:
                tax_ids = taxes.ids
            res['invoice_line_ids'][0][2]['tax_ids'] = [(6, 0, tax_ids)]

        return res
