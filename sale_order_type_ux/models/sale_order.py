##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    type_id = fields.Many2one(
        tracking=True,
    )

    def _change_values_from_type(self):
        for order in self:
            order_type = order.type_id
            if order_type.team_id:
                order.team_id = order_type.team_id
            if order_type.analytic_account_id:
                order.analytic_account_id = order_type.analytic_account_id
            order._compute_fiscal_position_id()

    @api.depends('partner_shipping_id', 'partner_id', 'company_id')
    def _compute_fiscal_position_id(self):
        if self.type_id.fiscal_position_id:
            self.fiscal_position_id = self.type_id.fiscal_position_id
        else:
            return super()._compute_fiscal_position_id()

    @api.onchange("type_id")
    def onchange_type_id(self):
        super().onchange_type_id()
        self._change_values_from_type()

    @api.model_create_multi
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
        self = self.with_company(company.id)
        if company != self.company_id:
            res['company_id'] = company.id
            res['partner_bank_id'] = company.partner_id.bank_ids[:1].id
            so_fiscal_position = self.env['account.fiscal.position'].browse(res['fiscal_position_id'])
            if so_fiscal_position.company_id and so_fiscal_position.company_id != company:
                res['fiscal_position_id'] = self.env['account.fiscal.position'].with_company(
                    company.id)._get_fiscal_position(self.partner_invoice_id).id
        return res
