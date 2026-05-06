##############################################################################
from odoo import Command, _, models
from odoo.exceptions import UserError


class SaleAdvancePaymentInvWizard(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _get_gathering_delivery_equivalent_taxes(self, taxes, company):
        mapped_taxes = self.env["account.tax"]
        for tax in taxes:
            if not tax.company_id or tax.company_id == company:
                mapped_taxes |= tax
                continue
            new_tax = self.env["account.tax"].search(
                [
                    ("type_tax_use", "=", tax.type_tax_use),
                    ("tax_group_id.name", "=", tax.tax_group_id.name),
                    ("amount", "=", tax.amount),
                    ("active", "=", True),
                    ("price_include_override", "=", tax.price_include_override),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            )
            if not new_tax:
                raise UserError(
                    _(
                        "The selected company (%s) does not have an equivalent tax to '%s' "
                        "(same type, group and amount)."
                    )
                    % (company.name, tax.name)
                )
            mapped_taxes |= new_tax
        return mapped_taxes

    def _prepare_gathering_delivery_invoice_line_vals(self, line, invoice):
        line_vals = line._prepare_invoice_line(quantity=line.product_uom_qty)
        line_vals["move_id"] = invoice.id
        if invoice.company_id != line.company_id:
            line_vals["tax_ids"] = [
                Command.set(self._get_gathering_delivery_equivalent_taxes(line.tax_id, invoice.company_id).ids)
            ]
            account_id = line_vals.get("account_id")
            if account_id and invoice.company_id not in self.env["account.account"].browse(account_id).company_ids:
                line_vals.pop("account_id")
        return line_vals

    def _create_invoices(self, sale_orders):
        invoice = super()._create_invoices(sale_orders)

        if self.advance_payment_method == "fixed" and sale_orders.filtered("is_gathering"):
            created_lines = self.env["account.move.line"]
            for order in sale_orders.filtered("is_gathering"):
                delivery_lines = order.order_line.filtered(lambda l: l.is_delivery and l.product_uom_qty > 0)
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

        return invoice
