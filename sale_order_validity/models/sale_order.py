from odoo import fields, models, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError


class SaleOrder(models.Model):

    _inherit = "sale.order"

    validity_days = fields.Integer(
        readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        help='Set days of validity for Sales Order',
    )

    validity_date = fields.Date(
        help="Date until when quotation is valid",
        track_visibility='onchange',
        states={},
    )

    date_order = fields.Datetime(
        copy=True,
    )

    @api.onchange('date_order', 'validity_days')
    @api.constrains('date_order', 'validity_days')
    def get_validity_date(self):
        for rec in self.filtered(lambda x: x.validity_days):
            date_order = fields.Datetime.from_string(rec.date_order)
            rec.validity_date = fields.Datetime.to_string(
                date_order + relativedelta(days=rec.validity_days))

    @api.onchange('company_id')
    @api.constrains('company_id')
    def onchange_company(self):
        for rec in self:
            rec.validity_days = rec.company_id.quotation_validity_days

    @api.onchange('validity_days')
    def onchange_validity_days(self):
        company_validity_days = self.company_id.quotation_validity_days
        if self.validity_days > company_validity_days:
            self.validity_days = self.company_id.quotation_validity_days
            warning = {
                'title': _('Warning!'),
                'message': _(
                    'You can not set more validity days than the configured on'
                    ' the company (%i days).' % company_validity_days),
            }
            return {'warning': warning}

    def _compute_is_expired(self):
        today = fields.Date.today()
        for order in self:
            order.is_expired = order.state == 'draft' and order.validity_date and order.validity_date < today
        if not order.is_expired:
            return super()._compute_is_expired()

    def action_confirm(self):
        self.ensure_one()
        if self.is_expired:
            raise UserError(_(
                'You can not confirm this quotation as it was valid until'
                ' %s! Please update validity.') % (self.validity_date))
        return super().action_confirm()

    def update_date_prices_and_validity(self):
        self.date_order = fields.Datetime.now()
        self.update_prices()
        self.onchange_company()
        return True
