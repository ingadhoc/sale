from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends("sale_line_ids", "company_id")
    def _compute_tax_ids(self):
        super()._compute_tax_ids()
        for line in self:
            # During cross-company operations on advance invoices with delivery lines
            # belonging to a *gathering* sale order, the native `sale` module re-injects
            # taxes from the original (old) company. Strip them out so the ORM constraint
            # does not raise "Incompatible companies". The multicompany wizard will
            # re-assign the correct equivalent taxes right after.
            # We scope this strictly to gathering orders to avoid masking legitimate
            # cross-company tax errors on regular sale orders.
            delivery_sale_lines = line.sale_line_ids.filtered(lambda sl: sl.is_delivery)
            if not delivery_sale_lines or not line.tax_ids:
                continue
            is_gathering = delivery_sale_lines.order_id.filtered("is_gathering")
            if not is_gathering:
                continue
            incompatible_taxes = line.tax_ids.filtered(lambda t: t.company_id and t.company_id != line.company_id)
            if incompatible_taxes:
                line.tax_ids -= incompatible_taxes
