from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    validity_days = fields.Integer(
        help="Set days of validity for Sales Order",
        compute="_compute_validity_days",
        readonly=False,
        store=True,
        precompute=True,
    )

    validity_date = fields.Date(
        help="Date until when quotation is valid",
        tracking=True,
    )

    date_order = fields.Datetime(
        copy=True,
    )

    @api.depends("date_order", "validity_days")
    def _compute_validity_date(self):
        orders = self.filtered(lambda x: x.date_order and x.validity_days)
        for rec in orders:
            rec.validity_date = rec.date_order.date() + timedelta(days=rec.validity_days)
        super(SaleOrder, self - orders)._compute_validity_date()

    @api.depends("company_id")
    def _compute_validity_days(self):
        for rec in self:
            rec.validity_days = rec.company_id.quotation_validity_days

    @api.constrains("validity_days")
    def _check_validity_days(self):
        for rec in self.filtered("validity_days"):
            if rec.validity_days > rec.company_id.quotation_validity_days:
                raise UserError(
                    _("You can not set more validity days than the configured on the company (%i days).")
                    % rec.company_id.quotation_validity_days
                )

    @api.constrains("validity_date", "date_order")
    def _check_validity_date(self):
        for rec in self.filtered(lambda r: r.validity_date and r.date_order):
            max_validity_date = rec.date_order.date() + timedelta(days=rec.company_id.quotation_validity_days)
            if rec.validity_date > max_validity_date:
                raise UserError(
                    _(
                        "The validity date (%s) exceeds the maximum allowed (%s) based on the company's quotation settings (%i days)."
                    )
                    % (
                        rec.validity_date.strftime("%Y-%m-%d"),
                        max_validity_date.strftime("%Y-%m-%d"),
                        rec.company_id.quotation_validity_days,
                    )
                )

    def action_confirm(self):
        for rec in self.filtered("is_expired"):
            raise UserError(
                _("You can not confirm this quotation as it was valid until" " %s! Please update validity.")
                % (rec.validity_date)
            )
        return super().action_confirm()

    def update_date_prices_and_validity(self):
        self.date_order = fields.Datetime.now()
        self.action_update_prices()
