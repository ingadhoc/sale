##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    # def _get_total_credit_all_companies(self, partner):
    #     credit = 0.0
    #     credit_to_invoice = 0.0
    #     for company in self.env["res.company"].search([]):
    #         credit += partner.with_context(force_company=company.id).credit
    #         credit_to_invoice += partner.with_context(force_company=company.id).credit_to_invoice
    #     return credit, credit_to_invoice

    # @api.model
    # def _build_credit_warning_message(self, record, current_amount=0.0, exclude_current=False, exclude_amount=0.0):
    #     partner = record.partner_id.commercial_partner_id

    #     # Patch: sumar créditos de todas las compañías
    #     credit, credit_to_invoice = self._get_total_credit_all_companies(partner)
    #     credit_to_invoice -= exclude_amount
    #     total_credit = credit + credit_to_invoice + current_amount

    #     if not partner.credit_limit or total_credit <= partner.credit_limit:
    #         return ""

    #     msg = _(
    #         "%(partner_name)s has reached its credit limit of: %(credit_limit)s",
    #         partner_name=partner.name,
    #         credit_limit=formatLang(self.env, partner.credit_limit, currency_obj=record.company_id.currency_id),
    #     )
    #     total_credit_formatted = formatLang(self.env, total_credit, currency_obj=record.company_id.currency_id)

    #     if credit_to_invoice > 0 and current_amount > 0:
    #         return (
    #             msg
    #             + "\n"
    #             + _(
    #                 "Total amount due (including sales orders and this document): %(total_credit)s",
    #                 total_credit=total_credit_formatted,
    #             )
    #         )
    #     elif credit_to_invoice > 0:
    #         return (
    #             msg
    #             + "\n"
    #             + _("Total amount due (including sales orders): %(total_credit)s", total_credit=total_credit_formatted)
    #         )
    #     elif current_amount > 0:
    #         return (
    #             msg
    #             + "\n"
    #             + _("Total amount due (including this document): %(total_credit)s", total_credit=total_credit_formatted)
    #         )
    #     else:
    #         return msg + "\n" + _("Total amount due: %(total_credit)s", total_credit=total_credit_formatted)
