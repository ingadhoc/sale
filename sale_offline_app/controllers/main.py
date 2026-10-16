import hashlib
import json
import re
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
from odoo import fields, http
from odoo.addons.base.models.res_users import INDEX_SIZE, KEY_CRYPT_CONTEXT
from odoo.http import request
from odoo.tools import SQL, file_open, html2plaintext
from werkzeug.exceptions import Forbidden, Unauthorized

APP_PATH = "/preventa"
BUNDLE = "sale_offline_app.assets"
API_KEY_SCOPE = "sale_offline_app"
API_KEY_MONTHS = 6
ORDERS_SCHEMA_VERSION = 1
ACTIVITY_DAYS_AHEAD = 7
ORDER_HISTORY_DAYS = 30
MAX_HISTORY_ORDERS = 500
MAX_REASON_LENGTH = 500
MAX_ORDERS_PER_REQUEST = 200
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
# Loaded on demand by web/core/barcode when the browser lacks BarcodeDetector.
LAZY_URLS = ["/web/static/lib/zxing-library/zxing-library.js"]


class SaleOfflineApp(http.Controller):
    def _asset_urls(self):
        return request.env["ir.qweb"]._get_asset_links(BUNDLE, debug=request.session.debug)

    def _precache_urls(self):
        return [APP_PATH, f"{APP_PATH}/manifest.webmanifest", *self._asset_urls(), *LAZY_URLS] + [
            f"/web/static/img/odoo-icon-{size}.png" for size in ("192x192", "512x512")
        ]

    def _session_info(self):
        # The shell page is cached by the service worker: it must not carry user data.
        info = request.env["ir.http"].get_frontend_session_info()
        info.update(uid=False, is_admin=False, is_system=False, is_public=True, is_internal_user=False)
        return info

    @http.route(APP_PATH, type="http", auth="public", methods=["GET"], sitemap=False)
    def app(self):
        return request.render(
            "sale_offline_app.index",
            {
                "session_info": self._session_info(),
                "debug": request.session.debug,
            },
        )

    @http.route(f"{APP_PATH}/manifest.webmanifest", type="http", auth="public", methods=["GET"], readonly=True)
    def webmanifest(self):
        manifest = {
            "name": "Preventa",
            "short_name": "Preventa",
            "id": APP_PATH + "/",
            "scope": APP_PATH,
            "start_url": APP_PATH,
            "display": "standalone",
            "orientation": "portrait",
            "background_color": "#714B67",
            "theme_color": "#714B67",
            "prefer_related_applications": False,
            # Lets the page ask the browser whether this same PWA is installed (getInstalledRelatedApps).
            "related_applications": [
                {"platform": "webapp", "url": f"{request.httprequest.host_url}{APP_PATH[1:]}/manifest.webmanifest"}
            ],
            "icons": [
                {"src": f"/web/static/img/odoo-icon-{size}.png", "sizes": size, "type": "image/png"}
                for size in ("192x192", "512x512")
            ],
        }
        return request.make_json_response(manifest, {"Content-Type": "application/manifest+json"})

    @http.route(f"{APP_PATH}/service-worker.js", type="http", auth="public", methods=["GET"], readonly=True)
    def service_worker(self):
        urls = self._precache_urls()
        # Asset URLs carry the bundle hash, so any JS/CSS change yields a new worker script.
        version = hashlib.sha1(json.dumps(urls).encode()).hexdigest()[:12]
        with file_open("sale_offline_app/static/src/sw/service_worker.js") as f:
            body = f.read()
        header = f"const VERSION = {json.dumps(version)};\nconst PRECACHE_URLS = {json.dumps(urls)};\n"
        return request.make_response(
            header + body,
            [
                ("Content-Type", "text/javascript"),
                ("Service-Worker-Allowed", APP_PATH),
                ("Cache-Control", "no-cache"),
            ],
        )

    @http.route(f"{APP_PATH}/link", type="http", auth="user", methods=["GET"], sitemap=False)
    def link(self):
        user = request.env.user
        if not user._is_internal():
            raise Forbidden()
        expiration = fields.Datetime.now() + relativedelta(months=API_KEY_MONTHS)
        # sudo lets the key outlive the max duration allowed to the user's groups.
        key = (
            request.env["res.users.apikeys"]
            .sudo()
            ._generate(API_KEY_SCOPE, f"Preventa {fields.Datetime.now()}", expiration)
        )
        # Expiration in UTC with an explicit "Z" so the device reads it in its own timezone.
        params = json.dumps({"key": key, "uid": user.id, "user": user.name, "expiration": expiration.isoformat() + "Z"})
        return request.redirect(f"{APP_PATH}#link={params}", local=True)

    def _bearer_token(self):
        header = request.httprequest.headers.get("Authorization") or ""
        match = re.match(r"^bearer\s+(.+)$", header, re.IGNORECASE)
        if not match:
            raise Unauthorized()
        return match.group(1)

    def _authenticate_bearer(self):
        uid = request.env["res.users.apikeys"]._check_credentials(scope=API_KEY_SCOPE, key=self._bearer_token())
        if not uid:
            raise Unauthorized()
        request.update_env(user=uid)
        return request.env.user

    @http.route(f"{APP_PATH}/api/logout", type="http", auth="none", methods=["POST"], csrf=False)
    def logout(self):
        """Revoke the API key used by the device, so a copied key stops working."""
        user = self._authenticate_bearer()
        token = self._bearer_token()
        request.env.cr.execute(
            SQL(
                "SELECT id, key FROM res_users_apikeys WHERE user_id = %s AND scope = %s AND index = %s",
                user.id,
                API_KEY_SCOPE,
                token[:INDEX_SIZE],
            )
        )
        key_ids = [key_id for key_id, hashed in request.env.cr.fetchall() if KEY_CRYPT_CONTEXT.verify(token, hashed)]
        request.env["res.users.apikeys"].browse(key_ids)._remove()
        return request.make_json_response({"revoked": len(key_ids)}, {"Cache-Control": "no-store"})

    @http.route(f"{APP_PATH}/api/sync", type="http", auth="none", methods=["POST"], csrf=False, readonly=True)
    def sync(self):
        user = self._authenticate_bearer()
        company = user.company_id
        partners = request.env["res.partner"].search(
            [("parent_id", "=", False), ("company_id", "in", [False, *user.company_ids.ids])]
        )
        warehouse = self._warehouse(user)
        products = request.env["product.product"].search([("sale_ok", "=", True)])
        free_qty = {
            product.id: product.free_qty for product in products.with_context(warehouse_id=warehouse.id, bin_size=True)
        }
        categories = request.env["product.category"].search([("id", "parent_of", products.categ_id.ids)])
        fiscal_position_model = request.env["account.fiscal.position"]
        fiscal_position_by_partner = {
            partner.id: fiscal_position_model._get_fiscal_position(partner) for partner in partners
        }
        fiscal_positions = fiscal_position_model.union(*fiscal_position_by_partner.values())
        taxes_by_product = {product.id: product.taxes_id._filter_taxes_by_company(company) for product in products}
        taxes = request.env["account.tax"].union(*taxes_by_product.values(), fiscal_positions.tax_ids)
        taxes |= taxes.flatten_taxes_hierarchy()
        pricelists = self._pricelists_to_sync(partners)
        currency = company.currency_id
        data = {
            "server_date": fields.Datetime.to_string(fields.Datetime.now()),
            "user": user.name,
            "pin": user.sudo().offline_app_pin or False,
            "currency": {
                "id": currency.id,
                "symbol": currency.symbol,
                "position": currency.position,
                "digits": currency.decimal_places,
                "decimal_places": currency.decimal_places,
                "rounding": currency.rounding,
            },
            "company": {
                "id": company.id,
                "tax_calculation_rounding_method": company.tax_calculation_rounding_method,
            },
            "partners": [self._partner_data(partner, fiscal_position_by_partner[partner.id]) for partner in partners],
            "warehouse": {"id": warehouse.id, "name": warehouse.name} if warehouse else False,
            "products": [
                self._product_data(product, taxes_by_product[product.id], free_qty[product.id])
                for product in products.with_context(bin_size=True)
            ],
            "categories": [
                {"id": category.id, "name": category.name, "parent_id": category.parent_id.id or False}
                for category in categories
            ],
            "history": self._history_data(user),
            # Like sale.order.line: a percentage rule shows as a discount only with this on.
            "discount_enabled": request.env["product.pricelist.item"]._is_discount_feature_enabled(),
            "pricelists": [
                {"id": pricelist.id, "name": pricelist.name, "currency_id": pricelist.currency_id.id}
                for pricelist in pricelists
            ],
            # Already in the order Odoo tries them (product.pricelist.item._order).
            "pricelist_items": [
                self._pricelist_item_data(item)
                for item in request.env["product.pricelist.item"].search([("pricelist_id", "in", pricelists.ids)])
            ],
            "taxes": [self._tax_data(tax) for tax in taxes],
            "activities": self._activities_data(user, set(partners.ids)),
            "fiscal_positions": [
                {
                    "id": position.id,
                    "name": position.name,
                    "tax_ids": position.tax_ids.ids,
                    "tax_map": {str(src): dest for src, dest in (position.tax_map or {}).items()},
                }
                for position in fiscal_positions
            ],
        }
        return request.make_json_response(data, {"Cache-Control": "no-store"})

    @http.route(f"{APP_PATH}/api/image/<int:product_id>", type="http", auth="none", methods=["GET"], readonly=True)
    def product_image(self, product_id):
        """Product thumbnail, only while online: images are never stored on the device."""
        self._authenticate_bearer()
        product = request.env["product.product"].search([("id", "=", product_id), ("sale_ok", "=", True)])
        if not product:
            raise Forbidden()
        stream = request.env["ir.binary"]._get_image_stream_from(product, "image_128")
        response = stream.get_response()
        # Not even the browser HTTP cache may keep it.
        response.headers["Cache-Control"] = "no-store"
        return response

    @http.route(f"{APP_PATH}/api/orders", type="http", auth="none", methods=["POST"], csrf=False)
    def receive_orders(self):
        self._authenticate_bearer()
        try:
            orders = json.loads(request.httprequest.get_data(as_text=True) or "{}").get("orders")
        except ValueError:
            orders = None
        if not isinstance(orders, list) or len(orders) > MAX_ORDERS_PER_REQUEST:
            return request.make_json_response(
                {"error": f"Expected a list of at most {MAX_ORDERS_PER_REQUEST} orders"}, status=400
            )
        valid, rejected = [], []
        for order in orders:
            values, reason = self._parse_order(order)
            if reason:
                rejected.append({"uuid": isinstance(order, dict) and order.get("uuid"), "reason": reason})
            else:
                valid.append(values)
        accepted = set(request.env["sale.offline.order"]._receive(valid))
        result = {
            "accepted": [values["uuid"] for values in valid if values["uuid"] in accepted],
            # Already received before: for the app this also means "Odoo has it".
            "duplicates": [values["uuid"] for values in valid if values["uuid"] not in accepted],
            "rejected": rejected,
        }
        return request.make_json_response(result, {"Cache-Control": "no-store"})

    def _parse_order(self, order):
        """Cheap shape checks only: business validation belongs to the conversion."""
        if not isinstance(order, dict):
            return None, "not an object"
        if order.get("schema_version") != ORDERS_SCHEMA_VERSION:
            return None, f"unsupported schema_version {order.get('schema_version')!r}"
        uuid = order.get("uuid")
        if not isinstance(uuid, str) or not UUID_RE.match(uuid):
            return None, "invalid uuid"
        kind = order.get("kind", "order")
        if kind == "no_purchase":
            reason = order.get("reason")
            if not isinstance(reason, str) or not reason.strip() or len(reason) > MAX_REASON_LENGTH:
                return None, "invalid reason"
            if not order.get("activity_id"):
                return None, "no activity"
        elif kind != "order":
            return None, f"unknown kind {kind!r}"
        elif not isinstance(order.get("lines"), list) or not order["lines"]:
            return None, "no lines"
        try:
            datetime.fromisoformat(order["created_on_device"].replace("Z", "+00:00"))
        except (KeyError, AttributeError, ValueError):
            return None, "invalid created_on_device"
        values = {"uuid": uuid, "payload": order}
        return values, None

    def _activities_data(self, user, partner_ids):
        """Pending sales visits of the user: overdue, today and the next days.

        An activity may hang on the customer itself or on any record with a
        customer (e.g. the opportunity of a salesperson/customer pair).
        """
        visit_type = request.env.ref("sale_offline_app.mail_activity_type_sales_visit")
        activities = request.env["mail.activity"].search(
            [
                ("activity_type_id", "=", visit_type.id),
                ("user_id", "=", user.id),
                ("date_deadline", "<=", date.today() + timedelta(days=ACTIVITY_DAYS_AHEAD)),
            ],
            order="date_deadline, id",
        )
        result = []
        for activity in activities:
            record = request.env[activity.res_model].browse(activity.res_id)
            if activity.res_model == "res.partner":
                partner = record
            elif "partner_id" in record._fields:
                partner = record.partner_id.commercial_partner_id
            else:
                continue
            if partner.id not in partner_ids:
                continue
            result.append(
                {
                    "id": activity.id,
                    "partner_id": partner.id,
                    "date_deadline": fields.Date.to_string(activity.date_deadline),
                    "summary": activity.summary or activity.activity_type_id.name,
                    "note": html2plaintext(activity.note or "").strip() or False,
                    "res_model": activity.res_model,
                    "res_id": activity.res_id,
                }
            )
        return result

    def _warehouse(self, user):
        """Warehouse whose stock the app shows: the user's default one, else the
        company's first. Where it should come from is still an open question."""
        return user.property_warehouse_id or request.env["stock.warehouse"].search(
            [("company_id", "=", user.company_id.id)], limit=1
        )

    def _pricelists_to_sync(self, partners):
        """Pricelists of the customers plus the ones their rules are based on."""
        pricelists = partners.property_product_pricelist
        to_check = pricelists
        while to_check:
            based_on = to_check.item_ids.base_pricelist_id - pricelists
            pricelists |= based_on
            to_check = based_on
        return pricelists

    def _pricelist_item_data(self, item):
        # Fields read by the app to mirror product.pricelist.item._compute_price.
        return {
            "id": item.id,
            "pricelist_id": item.pricelist_id.id,
            "applied_on": item.applied_on,
            "categ_id": item.categ_id.id or False,
            "product_tmpl_id": item.product_tmpl_id.id or False,
            "product_id": item.product_id.id or False,
            "min_quantity": item.min_quantity,
            "date_start": item.date_start and fields.Datetime.to_string(item.date_start),
            "date_end": item.date_end and fields.Datetime.to_string(item.date_end),
            "base": item.base,
            "base_pricelist_id": item.base_pricelist_id.id or False,
            "compute_price": item.compute_price,
            "fixed_price": item.fixed_price,
            "percent_price": item.percent_price,
            "price_discount": item.price_discount,
            "price_markup": item.price_markup,
            "price_round": item.price_round,
            "price_surcharge": item.price_surcharge,
            "price_min_margin": item.price_min_margin,
            "price_max_margin": item.price_max_margin,
        }

    def _history_data(self, user):
        """Recent sale orders of the salesperson, so the app can show and repeat them."""
        orders = request.env["sale.order"].search(
            [
                ("user_id", "=", user.id),
                ("state", "!=", "cancel"),
                ("date_order", ">=", fields.Datetime.now() - timedelta(days=ORDER_HISTORY_DAYS)),
            ],
            order="date_order desc, id desc",
            limit=MAX_HISTORY_ORDERS,
        )
        return [
            {
                "id": order.id,
                "name": order.name,
                "partner_id": order.partner_id.commercial_partner_id.id,
                "partner_name": order.partner_id.commercial_partner_id.name,
                # UTC with an explicit "Z" so the device shows it in its own timezone.
                "date_order": order.date_order.isoformat() + "Z",
                "amount_total": order.amount_total,
                "state": order.state,
                "offline_uuid": order.offline_order_id.uuid or False,
                "lines": [
                    {
                        "product_id": line.product_id.id,
                        "name": line.product_id.display_name,
                        "quantity": line.product_uom_qty,
                        "price_unit": line.price_unit,
                    }
                    for line in order.order_line
                    if line.product_id and not line.display_type
                ],
            }
            for order in orders
        ]

    def _partner_data(self, partner, fiscal_position):
        return {
            "id": partner.id,
            "name": partner.name,
            "ref": partner.ref or False,
            "vat": partner.vat or False,
            "street": partner.street or False,
            "street2": partner.street2 or False,
            "city": partner.city or False,
            "zip": partner.zip or False,
            "state_id": partner.state_id.display_name or False,
            "country_id": partner.country_id.name or False,
            "phone": partner.phone or False,
            "email": partner.email or False,
            "partner_latitude": partner.partner_latitude,
            "partner_longitude": partner.partner_longitude,
            "property_product_pricelist": partner.property_product_pricelist.display_name or False,
            "pricelist_id": partner.property_product_pricelist.id or False,
            "fiscal_position_id": fiscal_position.id or False,
            "fiscal_position_name": fiscal_position.name or False,
        }

    def _product_data(self, product, taxes, free_qty):
        return {
            "id": product.id,
            "display_name": product.display_name,
            "default_code": product.default_code or False,
            "barcode": product.barcode or False,
            "lst_price": product.lst_price,
            "standard_price": product.standard_price,
            # Snapshot at sync time: it does not follow what is sold during the day.
            "free_qty": free_qty if product.is_storable else False,
            "product_tmpl_id": product.product_tmpl_id.id,
            "uom_id": product.uom_id.name,
            "taxes_id": taxes.ids,
            "categ_id": product.categ_id.id or False,
            # Read with bin_size: only tells whether there is an image to fetch online.
            "has_image": bool(product.image_128),
        }

    def _tax_data(self, tax):
        # Fields read by accountTaxHelpers (account/static/src/helpers/account_tax.js).
        return {
            "id": tax.id,
            "name": tax.name,
            "amount_type": tax.amount_type,
            "amount": tax.amount,
            "price_include": tax.price_include,
            "include_base_amount": tax.include_base_amount,
            "is_base_affected": tax.is_base_affected,
            "has_negative_factor": tax.has_negative_factor,
            "sequence": tax.sequence,
            "children_tax_ids": tax.children_tax_ids.ids,
            "tax_group_id": tax.tax_group_id.id,
            "fiscal_position_ids": tax.fiscal_position_ids.ids,
        }
