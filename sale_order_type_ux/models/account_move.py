##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("sale_type_id")
    def _compute_sale_type_id(self):
        super()._compute_sale_type_id()
        for record in self:
            if record.sale_type_id.journal_id:
                record._onchange_journal()
            if (
                record.sale_type_id
                and record.sale_type_id.journal_id.company_id.id not in record.env.companies.ids
                and not record.partner_id
            ):
                record.sale_type_id = self.env["sale.order.type"].search(
                    [
                        ("company_id", "in", [record.company_id.id, False]),
                        "|",
                        ("journal_id", "=", False),
                        ("journal_id.company_id", "=", record.company_id.id),
                    ],
                    limit=1,
                )

    @api.onchange("journal_id")
    def _onchange_journal(self):
        if self.journal_id and self.journal_id.currency_id:
            new_currency = self.journal_id.currency_id
            if new_currency != self.currency_id:
                self.currency_id = new_currency
                self._compute_currency_rate()
        if self.state == "draft" and self._get_last_sequence() and self.name and self.name != "/":
            self.name = "/"
