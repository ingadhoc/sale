##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _prepare_invoice_values(self, order, so_line, accounts):
        """
        Forzamos compania de diario de sale type
        """
        if not order.type_id.journal_id:
            return super()._prepare_invoice_values(order, so_line, accounts)
        company = order.type_id.journal_id.company_id
        self = self.with_company(company.id)
        res = super()._prepare_invoice_values(order, so_line, accounts)
        if company.id != order.company_id:
            for line_downpayment in so_line.filtered("is_downpayment"):
                tax = line_downpayment.tax_id
                if order.fiscal_position_id and tax:
                    tax_ids = order.fiscal_position_id.map_tax(tax).ids
                else:
                    tax_ids = tax.ids

                for line in res["invoice_line_ids"]:
                    if line[2]["is_downpayment"] and line[2]["sale_line_ids"][0][1] == line_downpayment.id:
                        line[2]["tax_ids"] = [(6, 0, tax_ids)]

        return res

    def _prepare_down_payment_product_values(self):
        res = super()._prepare_down_payment_product_values()
        if res["company_id"]:
            res["company_id"] = False
        return res
