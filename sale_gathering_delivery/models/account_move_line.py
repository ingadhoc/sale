from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _strip_gathering_incompatible_taxes(self):
        """Remove taxes that belong to a different company than the invoice line.
        Must be called within a _sync_dynamic_lines context so that _sync_tax_lines
        regenerates the corresponding tax accounting entries.
        """
        for line in self:
            delivery_sale_lines = line.sale_line_ids.filtered(lambda sl: sl.is_delivery)
            if not delivery_sale_lines or not line.tax_ids:
                continue
            if not delivery_sale_lines.order_id.filtered("is_gathering"):
                continue
            incompatible_taxes = line.tax_ids.filtered(lambda t: t.company_id and t.company_id != line.company_id)
            if incompatible_taxes:
                line.tax_ids -= incompatible_taxes
