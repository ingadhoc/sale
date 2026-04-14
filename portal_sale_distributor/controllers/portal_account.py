##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _
from odoo.addons.account.controllers.portal import PortalAccount
from odoo.addons.sale.controllers.portal import CustomerPortal
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


class CustomerPortalDistributor(CustomerPortal):

    def _prepare_quotations_domain(self, partner):
        domain = super()._prepare_quotations_domain(partner)
        for i, leaf in enumerate(domain):
            if isinstance(leaf, (list, tuple)) and leaf[0] == 'state':
                states = list(leaf[2])
                if 'draft' not in states:
                    states.insert(0, 'draft')
                domain[i] = (leaf[0], leaf[1], states)
                break
        return domain
