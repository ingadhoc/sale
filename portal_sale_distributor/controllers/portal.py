##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, http
from odoo.http import Controller, request, content_disposition
from datetime import datetime, timedelta


class PortalSummary(Controller):

    @http.route(['/my/summary', '/my/summary/page/<int:page>'],
                type='http', auth="user", website=True)
    def portal_my_summary(self, **kw):
        partner = request.env.user.partner_id
        to_date = fields.Datetime.to_string(datetime.now())
        from_date = fields.Datetime.to_string(
            datetime.now() + timedelta(days=-30))
        report_data = {
            'secondary_currency': False,
            'financial_amounts': False,
            'result_selection': 'all',
            'company_type': 'group_by_company',
            'company_id': False,
            'from_date': from_date,
            'to_date': to_date,
            'historical_full': True,
            'show_invoice_detail': False,
            'lang': partner.lang,
        }
        xls = request.env.ref(
            'account_debt_management.account_debt_report').sudo(
        ).with_context(report_data).render([partner.id], data=report_data)[0]
        xlshttpheaders = [
            ('Content-Type', 'application/vnd.ms-excel'),
            ('Content-Length', len(xls)),
            ('Content-Disposition',
             content_disposition('Resumen de Cuenta' + '.xls'))]
        return request.make_response(xls, headers=xlshttpheaders)

    @http.route(['/my/open_invoices', '/my/open_invoices/page/<int:page>'],
                type='http', auth="user", website=True)
    def portal_my_open_invoices(self, **kw):
        partner = request.env.user.partner_id
        report_data = {
            'secondary_currency': False,
            'financial_amounts': False,
            'result_selection': 'all',
            'company_type': 'group_by_company',
            'company_id': False,
            'to_date': False,
            'historical_full': False,
            'show_invoice_detail': False,
            'lang': partner.lang,
        }
        xls = request.env.ref(
            'account_debt_management.account_debt_report').sudo(
        ).with_context(report_data).render([partner.id], data=report_data)[0]
        xlshttpheaders = [
            ('Content-Type', 'application/vnd.ms-excel'),
            ('Content-Length', len(xls)),
            ('Content-Disposition',
             content_disposition('Factura Abiertas' + '.xls'))]
        return request.make_response(xls, headers=xlshttpheaders)
