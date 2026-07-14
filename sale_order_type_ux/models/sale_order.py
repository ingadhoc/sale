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
        if res.type_id and self.env.context.get("website_id"):
            res._compute_fiscal_position_id()
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
        Also creates separate invoices for each sale order type when multiple types are present.
        """
        # If we have multiple order types and not explicitly grouped, create separate invoices per type
        if len(self.mapped("type_id")) > 1 and not grouped:
            all_invoices = self.env["account.move"]
            for order_type in self.mapped("type_id"):
                orders_with_type = self.filtered(lambda x: x.type_id.id == order_type.id)
                type_invoices = super(SaleOrder, orders_with_type)._create_invoices(
                    grouped=grouped, final=final, date=date
                )
                all_invoices |= type_invoices
            invoices = all_invoices
        else:
            invoices = super()._create_invoices(grouped=grouped, final=final, date=date)

        return invoices

    def _get_protected_fields(self):
        return super()._get_protected_fields() + ["type_id"]

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        if self.type_id.invoice_company_id and self.type_id.invoice_company_id != self.company_id:
            res["company_id"] = self.type_id.invoice_company_id.id
        return res
