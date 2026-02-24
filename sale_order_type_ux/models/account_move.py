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
                and record.sale_type_id.journal_id
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
        if self.state == "draft" and self._get_last_sequence() and self.name and self.name != "/":
            self.name = "/"

    def action_post(self):
        """Procesa los anticipos multi-compañía al confirmar la factura."""
        res = super().action_post()
        for rec in self:
            dp_lines = rec.line_ids.sale_line_ids.filtered(lambda l: l.is_downpayment and not l.display_type)
            downpayment_lines = dp_lines.filtered(lambda sol: not sol.order_id.locked)
            for so_dpl in downpayment_lines:
                # Si la compañía de la línea de venta difiere de la compañía de la factura,
                # es necesario ajustar los impuestos para escenarios multi-compañía

                if so_dpl.company_id != rec.company_id:
                    fp_tax_groups = self.env["account.tax.group"]
                    original_taxes = {
                        so_dpl.id: line.tax_ids.filtered(lambda x: x.tax_group_id not in fp_tax_groups).ids[:]
                        for line in rec.invoice_line_ids
                    }
                    journal = rec.sale_type_id.journal_id or (
                        self.env["account.move"]
                        .new(
                            {
                                "move_type": rec.move_type,
                                "partner_id": rec.partner_id.id,
                                "company_id": so_dpl.company_id.id,
                            }
                        )
                        .journal_id
                    )
                    acc = self.env["account.change.company"].create(
                        {
                            "move_id": rec.id,
                            "company_ids": [so_dpl.company_id.id, rec.company_id.id],
                            "company_id": so_dpl.company_id.id,
                            "journal_id": journal.id,
                        }
                    )
                    # Aplicar el cambio de impuestos según la nueva compañía
                    acc._get_change_company_line_taxes(so_dpl, original_taxes)
        return res
