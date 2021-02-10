##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def product_id_change(self):
        if self.order_id.type_id.analytic_tag_ids:
            self.analytic_tag_ids = self.order_id.type_id.analytic_tag_ids
        return super().product_id_change()

    def _prepare_invoice_line(self):
        """
        Forzamos compania de diario de sale type
        """
        if not self.order_id.type_id.journal_id:
            return super()._prepare_invoice_line()
        company = self.order_id.type_id.journal_id.company_id
        self = self.with_context(force_company=company.id)
        res = super()._prepare_invoice_line()

        if company != self.company_id:
            # Because we not have the access to the invoice, we obtain the fiscal position who
            # has the invoice really
            fpos_id = self.env['account.fiscal.position'].with_context(
                force_company=company.id).get_fiscal_position(
                self.order_id.partner_id.id,
                self.order_id.partner_shipping_id.id)
            fpos = self.env['account.fiscal.position'].browse(fpos_id)
            taxes = self.product_id.taxes_id.filtered(
                lambda r: company == r.company_id)
            taxes = fpos.map_tax(taxes) if fpos else taxes
            res['tax_ids'] = [(6, 0, taxes.ids)]
        return res

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.order_id.type_id and res.order_id.type_id.analytic_tag_ids and not res.analytic_tag_ids:
            res.analytic_tag_ids = res.order_id.type_id.analytic_tag_ids
        return res
