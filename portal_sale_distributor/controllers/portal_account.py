##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _
from odoo.addons.account.controllers.portal import PortalAccount
from odoo.http import request


class PortalDistributorAccount(PortalAccount):

    def _get_invoice_domain(self):
        partner = request.env.user.partner_id
        domain = [('move_type', 'in', ['out_invoice', 'out_refund']),
                  ('message_partner_ids', 'child_of',
                   [partner.commercial_partner_id.id]),
                  ('state', 'in', ['posted', 'cancel'])]
        return domain

    def _get_account_searchbar_filters(self):
        return {
            'all': {'label': _('All'), 'domain': []},
            'invoices': {'label': _('Invoices'), 'domain': [('move_type', '=', ('out_invoice', 'out_refund'))]},
            'bills': {'label': _('Bills'), 'domain': [('move_type', '=', ('in_invoice', 'in_refund'))]},
            'open': {'label': _('Open'), 'domain': [('state', '=', 'posted'), ('payment_state', '=', 'not_paid')]},
        }
