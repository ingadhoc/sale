##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    type_id = fields.Many2one(
        track_visibility='onchange',
        readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
    )

    def _change_values_from_type(self):
        for order in self:
            order_type = order.type_id
            if order_type.team_id:
                order.team_id = order_type.team_id
            if order_type.analytic_tag_ids:
                order.order_line.analytic_tag_ids = order_type.analytic_tag_ids
            if order_type.analytic_account_id:
                order.analytic_account_id = order_type.analytic_account_id
            order.onchange_partner_shipping_id()

    @api.onchange('partner_shipping_id', 'partner_id', 'company_id')
    def onchange_partner_shipping_id(self):
        if self.type_id.fiscal_position_id:
            self.fiscal_position_id = self.type_id.fiscal_position_id
        else:
            return super().onchange_partner_shipping_id()

    @api.onchange("type_id")
    def onchange_type_id(self):
        super().onchange_type_id()
        self._change_values_from_type()

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.type_id and self._context.get('website_id'):
            res._change_values_from_type()
        return res

    def _prepare_invoice(self):
        if not self.type_id.journal_id:
            return super()._prepare_invoice()
        res = super()._prepare_invoice()
        company = self.type_id.journal_id.company_id
        self = self.with_context(force_company=company.id)
        if company != self.company_id:
            res['company_id'] = company.id
            res['invoice_partner_bank_id'] = company.partner_id.bank_ids[:1].id
            so_fiscal_position = self.env['account.fiscal.position'].browse(res['fiscal_position_id'])
            if so_fiscal_position.company_id and so_fiscal_position.company_id != company:
                res['fiscal_position_id'] = self.env['account.fiscal.position'].with_context(
                    force_company=company.id).get_fiscal_position(
                    self.partner_invoice_id.id, self.partner_shipping_id.id)
        return res
