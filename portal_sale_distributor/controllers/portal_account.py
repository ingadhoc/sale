##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import http, _
from odoo.addons.account.controllers.portal import PortalAccount
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.http import request
from collections import OrderedDict


class PortalDistributorAccount(PortalAccount):

    def _get_account_invoice_domain(self):
        partner = request.env.user.partner_id
        domain = [('type', 'in', ['out_invoice', 'out_refund']),
                  ('message_partner_ids', 'child_of',
                   [partner.commercial_partner_id.id]),
                  ('state', 'in', ['posted', 'cancel'])]
        return domain

    @http.route()
    def portal_my_invoices(
            self, page=1, date_begin=None, date_end=None, sortby=None,
            filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        AccountInvoice = request.env['account.move']

        domain = self._get_account_invoice_domain()
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'open': {'label': _('Open'),
                     'domain': [('state', '=', 'posted'), ('invoice_payment_state', '=', 'not_paid')]},
        }

        searchbar_sortings = {
            'date': {'label': _('Invoice Date'), 'order': 'invoice_date desc'},
            'duedate': {'label': _('Due Date'), 'order': 'invoice_date_due desc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        # default sort by order
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        archive_groups = self._get_archive_groups('account.move', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]

        # count for pager
        invoice_count = AccountInvoice.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/invoices",
            url_args={'date_begin': date_begin, 'date_end': date_end,
                      'sortby': sortby, 'filterby': filterby},
            total=invoice_count, page=page, step=self._items_per_page)
        # content according to pager and archive selected
        invoices = AccountInvoice.search(
            domain, order=order, limit=self._items_per_page,
            offset=pager['offset'])
        values.update({
            'date': date_begin,
            'invoices': invoices,
            'page_name': 'invoice',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/invoices',
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': OrderedDict(
                sorted(searchbar_filters.items())),
            'sortby': sortby,
            'filterby': filterby,
        })
        return request.render("account.portal_my_invoices", values)
