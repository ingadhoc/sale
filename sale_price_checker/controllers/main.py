##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import http
from odoo.http import request
from odoo.tools.misc import format_amount


class PriceCheckerController(http.Controller):
    def _pricelists_enabled(self):
        """True when the Pricelists feature is turned on in Sales settings.

        Mirrors the way the settings toggle works: pricelists are enabled
        when ``product.group_product_pricelist`` is implied by
        ``base.group_user``.
        """
        pricelist_group = request.env.ref("product.group_product_pricelist", raise_if_not_found=False)
        if not pricelist_group:
            return False
        return pricelist_group in request.env.ref("base.group_user").sudo().implied_ids

    def _resolve(self, company_id=None, pricelist_id=None):
        """Return (company, pricelist) or None if any id is invalid/archived.

        When ``company_id`` is ``None`` (bare ``/price-checker`` URL), pick
        the first active company by ``sequence`` (same ordering Odoo uses
        for the company switcher).

        ``pricelist`` may be an empty recordset — that's the ``lst_price``
        fallback path downstream. It happens when no override is requested
        and either the company has no default pricelist configured or the
        Pricelists feature is turned off system-wide.

        When ``pricelist_id`` is passed in the URL but the Pricelists
        feature is off, the URL form is rejected (returns ``None``).
        """
        if company_id is None:
            company = request.env["res.company"].sudo().search([], order="sequence, id", limit=1)
        else:
            company = request.env["res.company"].sudo().search([("id", "=", company_id)], limit=1)
        if not company:
            return None

        pricelists_enabled = self._pricelists_enabled()

        if pricelist_id is None:
            pricelist = (
                company.price_checker_pricelist_id.filtered("active")
                if pricelists_enabled
                else request.env["product.pricelist"].sudo()
            )
        else:
            if not pricelists_enabled:
                return None
            pricelist = (
                request.env["product.pricelist"]
                .sudo()
                .search(
                    [
                        ("id", "=", pricelist_id),
                        ("active", "=", True),
                        ("company_id", "in", (False, company.id)),
                    ],
                    limit=1,
                )
            )
            if not pricelist:
                return None

        return company, pricelist

    @http.route(
        [
            "/price-checker",
            "/price-checker/<int:company_id>",
            "/price-checker/<int:company_id>/<int:pricelist_id>",
            "/price-checker/-/<int:pricelist_id>",
        ],
        type="http",
        auth="public",
        methods=["GET"],
        website=True,
        multilang=False,
    )
    def page(self, company_id=None, pricelist_id=None, **kw):
        resolved = self._resolve(company_id, pricelist_id)
        if not resolved:
            return request.not_found()
        company, pricelist = resolved
        session_info = request.env["ir.http"].get_frontend_session_info()
        return request.render(
            "sale_price_checker.page",
            {
                "company": company,
                "pricelist": pricelist,
                "session_info": session_info,
                "lang": request.env.context.get("lang", "en_US"),
            },
        )

    @http.route(
        "/price-checker/<int:company_id>/lookup",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
    )
    def lookup(self, company_id, barcode=None, pricelist_id=None):
        resolved = self._resolve(company_id, pricelist_id)
        barcode = str(barcode or "").strip()
        if not resolved or not barcode:
            return {"found": False}
        company, pricelist = resolved

        env = request.env(context=dict(request.env.context, allowed_company_ids=[company.id]))
        product = (
            env["product.product"]
            .sudo()
            .search(
                [
                    ("barcode", "=", barcode),
                    ("sale_ok", "=", True),
                    ("product_tmpl_id.show_in_price_checker", "=", True),
                    ("company_id", "in", (False, company.id)),
                ],
                limit=1,
            )
        )
        if not product:
            return {"found": False}

        if pricelist:
            price = pricelist._get_product_price(product, 1.0)
            currency = pricelist.currency_id
        else:
            price = product.lst_price
            currency = company.currency_id

        taxes = product.taxes_id.filtered(lambda t: not t.company_id or t.company_id == company)
        if taxes:
            total = taxes.compute_all(price, currency, 1.0, product=product)["total_included"]
        else:
            total = price

        return {
            "found": True,
            "name": product.display_name,
            "description_sale": product.description_sale or "",
            "image_url": f"/price-checker/image/{product.id}",
            "price": format_amount(env, total, currency, lang_code=company.partner_id.lang),
            "price_untaxed": (
                format_amount(env, price, currency, lang_code=company.partner_id.lang) if taxes else False
            ),
        }

    @http.route(
        "/price-checker/image/<int:product_id>",
        type="http",
        auth="public",
        methods=["GET"],
    )
    def image(self, product_id, **kw):
        product = (
            request.env["product.product"]
            .sudo()
            .search(
                [
                    ("id", "=", product_id),
                    ("sale_ok", "=", True),
                    ("product_tmpl_id.show_in_price_checker", "=", True),
                ],
                limit=1,
            )
        )
        if not product:
            return request.not_found()
        return request.env["ir.binary"]._get_image_stream_from(product, "image_512").get_response()
