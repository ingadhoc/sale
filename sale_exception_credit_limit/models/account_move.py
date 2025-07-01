##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, _
from odoo.tools import formatLang


class AccountMove(models.Model):
    _inherit = "account.move"


    def _build_credit_warning_message(self, record, current_amount=0.0, exclude_current=False, exclude_amount=0.0):
        """ We override the original odoo method to change the total_credit (only that we change from the original method). We make it consider partner_id.credit_with_confirmed_orders and subtract partner_id.credit_to_invoice. """
        partner_id = record.partner_id.commercial_partner_id
        credit_to_invoice = partner_id.credit_to_invoice - exclude_amount
        ## Cambiamos credit por credit_with_confirmed_orders.
        total_credit = partner_id.credit_with_confirmed_orders - partner_id.credit_to_invoice + credit_to_invoice + current_amount
        ##
        if not partner_id.credit_limit or total_credit <= partner_id.credit_limit:
            return ''
        msg = _(
            '%(partner_name)s has reached its credit limit of: %(credit_limit)s',
            partner_name=partner_id.name,
            credit_limit=formatLang(self.env, partner_id.credit_limit, currency_obj=record.company_id.currency_id)
        )
        total_credit_formatted = formatLang(self.env, total_credit, currency_obj=record.company_id.currency_id)
        if credit_to_invoice > 0 and current_amount > 0:
            return msg + '\n' + _(
                'Total amount due (including sales orders and this document): %(total_credit)s',
                total_credit=total_credit_formatted
            )
        elif credit_to_invoice > 0:
            return msg + '\n' + _(
                'Total amount due (including sales orders): %(total_credit)s',
                total_credit=total_credit_formatted
            )
        elif current_amount > 0:
            return msg + '\n' + _(
                'Total amount due (including this document): %(total_credit)s',
                total_credit=total_credit_formatted
            )
        else:
            return msg + '\n' + _(
                'Total amount due: %(total_credit)s',
                total_credit=total_credit_formatted
            )
