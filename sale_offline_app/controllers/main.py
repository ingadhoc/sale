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
        products = request.env["product.product"].search([("sale_ok", "=", True)])
        fiscal_position_model = request.env["account.fiscal.position"]
        fiscal_position_by_partner = {
            partner.id: fiscal_position_model._get_fiscal_position(partner) for partner in partners
        }
        fiscal_positions = fiscal_position_model.union(*fiscal_position_by_partner.values())
        taxes_by_product = {product.id: product.taxes_id._filter_taxes_by_company(company) for product in products}
        taxes = request.env["account.tax"].union(*taxes_by_product.values(), fiscal_positions.tax_ids)
        taxes |= taxes.flatten_taxes_hierarchy()
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
            "products": [self._product_data(product, taxes_by_product[product.id]) for product in products],
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
        if not isinstance(order.get("lines"), list) or not order["lines"]:
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
            "fiscal_position_id": fiscal_position.id or False,
            "fiscal_position_name": fiscal_position.name or False,
        }

    def _product_data(self, product, taxes):
        return {
            "id": product.id,
            "display_name": product.display_name,
            "default_code": product.default_code or False,
            "barcode": product.barcode or False,
            "lst_price": product.lst_price,
            "uom_id": product.uom_id.name,
            "taxes_id": taxes.ids,
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
