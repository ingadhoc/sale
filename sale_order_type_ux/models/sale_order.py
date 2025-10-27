##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    type_id = fields.Many2one(
        tracking=True,
    )

    @api.depends("partner_shipping_id", "partner_id", "company_id", "type_id")
    def _compute_fiscal_position_id(self):
        if self.type_id.fiscal_position_id:
            self.fiscal_position_id = self.type_id.fiscal_position_id
        else:
            return super()._compute_fiscal_position_id()

    @api.model_create_multi
    def create(self, vals):
        res = super().create(vals)
        if res.type_id and self._context.get("website_id"):
            res._compute_fiscal_position_id()
        return res

    def _prepare_invoice(self):
        if not self.type_id.journal_id:
            return super()._prepare_invoice()
        res = super()._prepare_invoice()
        company = self.type_id.journal_id.company_id
        # self = self.with_company(company.id)
        journal = self.env["account.journal"].browse(res.get("journal_id")) if res.get("journal_id") else False
        if company != self.company_id:
            # agregamos para que recompute term y cond si la nueva compañia los tiene por defecto
            if "narration" in res and not res["narration"]:
                del res["narration"]

            if journal and journal.company_id.id != self.company_id.id:
                res.pop("journal_id")
        return res

    def _compute_team_id(self):
        res = super()._compute_team_id()
        for order in self.filtered("type_id"):
            order_type = order.type_id
            if order_type.team_id:
                order.team_id = order_type.team_id
        return res

    @api.onchange("type_id")
    def _onchange_team_id(self):
        if self.type_id and self.type_id.team_id:
            self.team_id = self.type_id.team_id

    def _create_invoices(self, grouped=False, final=False, date=None):
        """
        Overrides the `_create_invoices` method to ensure that taxes are correctly computed
        for the company of the invoice. In cases where the company has a localization
        (e.g., l10n_ar), this ensures that the taxes from `l10n_ar_tax_ids` are applied.
        """
        invoices = super()._create_invoices(grouped=grouped, final=final, date=date)
        for invoice in invoices.filtered("sale_type_id.journal_id"):
            company = invoice.sale_type_id.journal_id.company_id
            if invoice.company_id != company:
                acc = self.env["account.change.company"].create(
                    {
                        "move_id": invoice.id,
                        "company_ids": [invoice.company_id.id, company.id],
                        "company_id": company.id,
                        "journal_id": invoice.sale_type_id.journal_id.id,
                    }
                )
                acc.change_company()
                invoice.partner_bank_id = company.partner_id.bank_ids[:1].id
        return invoices

    def _get_protected_fields(self):
        return super()._get_protected_fields() + ["type_id"]
