##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    type_id = fields.Many2one(
        track_visibility='onchange',
        readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
    )

    def _prepare_invoice(self):
        if not self.type_id.journal_id:
            return super()._prepare_invoice()
        res = super()._prepare_invoice()
        company = self.type_id.journal_id.company_id
        self = self.with_context(force_company=company.id)
        if company != self.company_id.id:
            res['invoice_partner_bank_id'] = company.partner_id.bank_ids[:1].id
            res['fiscal_position_id'] = self.fiscal_position_id.id or\
                self.partner_invoice_id.property_account_position_id.id,
        return res
