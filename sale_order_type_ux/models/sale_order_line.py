##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        """
        Forzamos compania de diario de sale type
        """
        if not self.order_id.type_id.journal_id:
            return super()._prepare_invoice_line(**optional_values)
        company = self.order_id.type_id.journal_id.company_id
        self = self.with_company(company.id)
        res = super()._prepare_invoice_line(**optional_values)

        if company != self.company_id:
            # Because we not have the access to the invoice, we obtain the fiscal position who
            # has the invoice really
            fpos = self.env['account.fiscal.position'].with_company(
                company.id)._get_fiscal_position(
                self.order_id.partner_id,
                self.order_id.partner_shipping_id)
            taxes = self.product_id.taxes_id.filtered(
                lambda r: company == r.company_id)
            taxes = fpos.map_tax(taxes) if fpos else taxes
            res['tax_ids'] = [(6, 0, taxes.ids)]
        return res
