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

        res = super()._prepare_invoice_values(order, so_line, accounts)
        journal = self.env["account.journal"].browse(res.get("journal_id")) if res.get("journal_id") else False
        if company.id != order.company_id.id and journal and journal.company_id.id != order.company_id.id:
            res.pop("journal_id")
        return res

    def _create_invoices(self, sale_orders):
        # if discount product has a company associated, we need to remove it before changing the company in invoice
        if self.mapped("sale_order_ids.type_id.journal_id.company_id") != self.mapped("sale_order_ids.company_id"):
            discount_lines = self.mapped("sale_order_ids.order_line").filtered(
                lambda x: x.product_id == self.company_id.sale_discount_product_id
            )
            if discount_lines and discount_lines.product_id.company_id:
                discount_lines[0].product_id.write({"company_id": False})
        res = super()._create_invoices(sale_orders)
        if sale_orders.type_id.journal_id:
            company = sale_orders.type_id.journal_id.company_id
            if company.id != sale_orders.company_id.id:
                acc = self.env["account.change.company"].create(
                    {
                        "move_id": res.id,
                        "company_ids": [sale_orders.company_id.id, company.id],
                        "company_id": company.id,
                        "journal_id": sale_orders.type_id.journal_id.id,
                    }
                )
                acc.change_company()
        return res
