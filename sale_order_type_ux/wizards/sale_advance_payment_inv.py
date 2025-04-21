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
        if company.id != order.company_id.id:
            for line_downpayment in so_line.filtered("is_downpayment"):
                tax = line_downpayment.tax_id
                # Buscamos el correcto tax para la compañia sobre la cual estoy facturando, siendo
                # esta distinta a la de la sale order line
                correct_company_tax = self.env["account.tax"].search(
                    [
                        ("company_id", "=", company.id),
                        ("type_tax_use", "=", tax.type_tax_use),
                        ("company_price_include", "=", tax.company_price_include),
                        ("amount", "=", tax.amount),
                    ]
                )
                if order.fiscal_position_id and correct_company_tax:
                    tax_ids = order.fiscal_position_id.map_tax(correct_company_tax).ids
                else:
                    tax_ids = correct_company_tax.ids or False

                for line in res["invoice_line_ids"]:
                    if line[2]["is_downpayment"] and line[2]["sale_line_ids"][0][1] == line_downpayment.id:
                        line[2]["tax_ids"] = [(6, 0, tax_ids)]

        return res
