##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from datetime import datetime, timedelta

from odoo import fields, http
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.http import Controller, content_disposition, request


class PortalSummary(Controller):
    @http.route(["/my/summary", "/my/summary/page/<int:page>"], type="http", auth="user", website=True)
    def portal_my_summary(self, **kw):
        partner = request.env.user.partner_id
        to_date = fields.Datetime.to_string(datetime.now())
        from_date = fields.Datetime.to_string(datetime.now() + timedelta(days=-30))
        report_data = {
            "secondary_currency": False,
            "financial_amounts": False,
            "result_selection": "all",
            "company_type": "group_by_company",
            "company_id": False,
            "from_date": from_date,
            "to_date": to_date,
            "historical_full": True,
            "show_invoice_detail": False,
            "lang": partner.lang,
        }
        xls = (
            request.env.ref("account_debt_management.account_debt_report")
            .sudo()
            .with_context(**report_data)
            .render([partner.id], data=report_data)[0]
        )
        xlshttpheaders = [
            ("Content-Type", "application/vnd.ms-excel"),
            ("Content-Length", len(xls)),
            ("Content-Disposition", content_disposition("Resumen de Cuenta" + ".xls")),
        ]
        return request.make_response(xls, headers=xlshttpheaders)

    @http.route(["/my/open_invoices", "/my/open_invoices/page/<int:page>"], type="http", auth="user", website=True)
    def portal_my_open_invoices(self, **kw):
        partner = request.env.user.partner_id
        report_data = {
            "secondary_currency": False,
            "financial_amounts": False,
            "result_selection": "all",
            "company_type": "group_by_company",
            "company_id": False,
            "to_date": False,
            "historical_full": False,
            "show_invoice_detail": False,
            "lang": partner.lang,
        }
        xls = (
            request.env.ref("account_debt_management.account_debt_report")
            .sudo()
            .with_context(**report_data)
            .render([partner.id], data=report_data)[0]
        )
        xlshttpheaders = [
            ("Content-Type", "application/vnd.ms-excel"),
            ("Content-Length", len(xls)),
            ("Content-Disposition", content_disposition("Factura Abiertas" + ".xls")),
        ]
        return request.make_response(xls, headers=xlshttpheaders)


class CustomerPortalDistributor(CustomerPortal):
    """Extend CustomerPortal to allow portal distributors to see quotations"""

    def _prepare_home_portal_values(self, counters):
        """Add quotation counter for distributors"""
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        # Agregar contador de quotations solo para portal distributors
        if request.env.user.has_group("portal_sale_distributor.group_portal_backend_distributor"):
            SaleOrder = request.env["sale.order"]
            if "quotation_count" in counters:
                values["quotation_count"] = (
                    SaleOrder.search_count(self._prepare_quotations_domain(partner))
                    if SaleOrder.has_access("read")
                    else 0
                )

        return values

    def _prepare_quotations_domain(self, partner):
        """Domain for quotations (draft and sent) (only for distributors)"""
        return [
            ("message_partner_ids", "child_of", [partner.commercial_partner_id.id]),
            ("state", "in", ["draft", "sent"]),
        ]

    @http.route(["/my/quotes", "/my/quotes/page/<int:page>"], type="http", auth="user", website=True)
    def portal_my_quotes(self, **kwargs):
        """Show quotations (draft and sent) for portal distributors"""
        if not request.env.user.has_group("portal_sale_distributor.group_portal_backend_distributor"):
            return request.redirect("/my")

        values = self._prepare_sale_portal_rendering_values(quotation_page=True, draft_page=True, **kwargs)
        request.session["my_quotations_history"] = values["quotations"].ids[:100]
        return request.render("portal_sale_distributor.portal_my_quotations", values)

    def _prepare_sale_portal_rendering_values(
        self, page=1, date_begin=None, date_end=None, sortby=None, quotation_page=False, draft_page=False, **kwargs
    ):
        """Override to support quotations page"""
        if draft_page and request.env.user.has_group("portal_sale_distributor.group_portal_backend_distributor"):
            SaleOrder = request.env["sale.order"]
            if not sortby:
                sortby = "date"

            partner = request.env.user.partner_id
            values = self._prepare_portal_layout_values()

            url = "/my/quotes"
            domain = self._prepare_quotations_domain(partner)

            searchbar_sortings = CustomerPortal._get_sale_searchbar_sortings(self)
            sort_order = searchbar_sortings[sortby]["order"]

            if date_begin and date_end:
                domain += [("create_date", ">", date_begin), ("create_date", "<=", date_end)]

            url_args = {"date_begin": date_begin, "date_end": date_end}
            if len(searchbar_sortings) > 1:
                url_args["sortby"] = sortby

            pager_values = portal_pager(
                url=url,
                total=SaleOrder.search_count(domain) if SaleOrder.has_access("read") else 0,
                page=page,
                step=self._items_per_page,
                url_args=url_args,
            )
            orders = (
                SaleOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager_values["offset"])
                if SaleOrder.has_access("read")
                else SaleOrder
            )

            values.update(
                {
                    "date": date_begin,
                    "quotations": orders.sudo(),
                    "orders": SaleOrder,
                    "page_name": "quote",
                    "pager": pager_values,
                    "default_url": url,
                }
            )

            if len(searchbar_sortings) > 1:
                values.update(
                    {
                        "sortby": sortby,
                        "searchbar_sortings": searchbar_sortings,
                    }
                )

            return values

        return super()._prepare_sale_portal_rendering_values(
            page=page, date_begin=date_begin, date_end=date_end, sortby=sortby, quotation_page=quotation_page, **kwargs
        )
