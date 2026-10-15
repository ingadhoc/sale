import { markRaw, reactive } from "@odoo/owl";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { roundPrecision } from "@web/core/utils/numbers";
import { LocalDB } from "./local_db";
import { PricelistEngine } from "./pricelist";

const APP_PATH = "/preventa";
// Bump when the shape of synced records changes: local catalog is refreshed, orders are kept.
const DATA_VERSION = 6;
const ORDERS_SCHEMA_VERSION = 1;
const ORDERS_PER_REQUEST = 200;
const AUTO_SEND_RETRY_MS = 60000;
// Back from background after this long counts as reopening the app (PWAs resumed
// from the recent apps list do not reload).
const RELOCK_AFTER_MS = 5 * 60 * 1000;
const EXPIRY_WARNING_DAYS = 7;
export const KEY_EXPIRY_WARNING_DAYS = EXPIRY_WARNING_DAYS;
const AUTH_EXPIRED_MESSAGE = "La vinculación con Odoo venció o fue revocada.";

function normalize(text) {
    return (text || "")
        .toString()
        .normalize("NFD")
        .replace(/[̀-ͯ]/g, "")
        .toLowerCase();
}

export const preventaService = {
    async start() {
        const db = new LocalDB();
        await db.open();

        const state = reactive({
            online: browser.navigator.onLine,
            link: null,
            lastSync: null,
            syncing: false,
            error: null,
            updateAvailable: false,
            needsSync: false,
            authExpired: false,
            pin: false,
            locked: false,
            autoSend: false,
            sending: false,
            lastSend: null,
            persisted: null,
            storage: null,
            currency: { symbol: "$", position: "before", digits: 2, decimal_places: 2, rounding: 0.01 },
            partners: [],
            products: [],
            activities: [],
            categories: [],
            history: [],
            orders: {},
            // Day of visits the salesperson chose to work on (kept while the app is open).
            workDay: null,
            // Customer search of the orders screen, kept while opening an order and coming back.
            ordersQuery: "",
            warehouse: false,
        });
        let pricing = markRaw(new PricelistEngine());
        let discountEnabled = false;
        let index = markRaw({ byCode: new Map(), byId: new Map() });
        let catalog = markRaw({ children: new Map(), products: new Map(), counts: new Map() });
        // Images are only shown online and never stored: object URLs live while the app is open.
        const imageUrls = new Map();
        let fiscal = markRaw({ company: null, taxById: new Map(), positionById: new Map() });
        let waitingWorker = null;

        function buildIndex() {
            const byCode = new Map();
            const byId = new Map(state.products.map((product) => [product.id, product]));
            for (const product of state.products) {
                product._search = normalize(
                    [product.display_name, product.default_code, product.barcode].join(" ")
                );
                for (const code of [product.barcode, product.default_code]) {
                    if (code) {
                        byCode.set(code, product);
                    }
                }
            }
            for (const partner of state.partners) {
                partner._search = normalize([partner.name, partner.ref, partner.vat].join(" "));
            }
            index = markRaw({ byCode, byId });
            buildCatalog();
        }

        /** Category tree for the catalog: children and products per category, and how
         * many products hang below each one (subcategories included). */
        function buildCatalog() {
            const parentById = new Map(state.categories.map((category) => [category.id, category.parent_id]));
            const children = new Map();
            for (const category of state.categories) {
                const key = category.parent_id || false;
                if (!children.has(key)) {
                    children.set(key, []);
                }
                children.get(key).push(category);
            }
            for (const list of children.values()) {
                list.sort((a, b) => a.name.localeCompare(b.name));
            }
            const products = new Map();
            const counts = new Map();
            for (const product of state.products) {
                const key = product.categ_id || false;
                if (!products.has(key)) {
                    products.set(key, []);
                }
                products.get(key).push(product);
                for (let id = key; id; id = parentById.get(id)) {
                    counts.set(id, (counts.get(id) || 0) + 1);
                }
            }
            for (const list of products.values()) {
                list.sort((a, b) => a.display_name.localeCompare(b.display_name));
            }
            catalog = markRaw({ children, products, counts });
        }

        function getCategoryChildren(categoryId) {
            return (catalog.children.get(categoryId || false) || []).filter((category) =>
                catalog.counts.get(category.id)
            );
        }

        function getCategoryProducts(categoryId) {
            return catalog.products.get(categoryId || false) || [];
        }

        function getCategoryCount(categoryId) {
            return catalog.counts.get(categoryId) || 0;
        }

        function buildFiscal(company, taxes, positions) {
            const taxById = new Map(taxes.map((tax) => [tax.id, { ...tax }]));
            for (const tax of taxById.values()) {
                // accountTaxHelpers expects tax records, not ids, for group taxes.
                tax.children_tax_ids = tax.children_tax_ids.map((id) => taxById.get(id)).filter(Boolean);
            }
            fiscal = markRaw({
                company: company && { ...company, currency_id: state.currency },
                taxById,
                positionById: new Map(positions.map((position) => [position.id, position])),
            });
        }

        // Mirror of account.fiscal.position.map_tax.
        function getTaxes(product, partner) {
            const taxes = (product.taxes_id || []).map((id) => fiscal.taxById.get(id)).filter(Boolean);
            const position = partner && fiscal.positionById.get(partner.fiscal_position_id);
            if (!position) {
                return taxes;
            }
            if (!position.tax_ids.length) {
                return taxes.filter((tax) => !tax.fiscal_position_ids.length);
            }
            const ids = new Set();
            for (const tax of taxes) {
                for (const id of position.tax_map[tax.id] || [tax.id]) {
                    ids.add(id);
                }
            }
            return [...ids].map((id) => fiscal.taxById.get(id)).filter(Boolean);
        }

        /**
         * Same computation as the PoS: one base line per order line, then rounding
         * over all of them, so totals match what Odoo computes on the sale order.
         */
        function computeLines(lines, partner) {
            const baseLines = lines.map((line) => {
                const product = index.byId.get(line.product_id) || { id: line.product_id, taxes_id: [] };
                return accountTaxHelpers.prepare_base_line_for_taxes_computation(null, {
                    product_id: product,
                    tax_ids: getTaxes(product, partner),
                    price_unit: line.price_unit,
                    quantity: line.quantity,
                    discount: line.discount || 0,
                    currency_id: state.currency,
                });
            });
            let excluded = 0;
            let included = 0;
            if (fiscal.company) {
                accountTaxHelpers.add_tax_details_in_base_lines(baseLines, fiscal.company);
                accountTaxHelpers.round_base_lines_tax_details(baseLines, fiscal.company);
            }
            const result = baseLines.map((baseLine) => {
                const details = baseLine.tax_details || {};
                const lineExcluded = details.total_excluded ?? baseLine.price_unit * baseLine.quantity;
                const lineIncluded = details.total_included ?? lineExcluded;
                excluded += lineExcluded;
                included += lineIncluded;
                return {
                    excluded: lineExcluded,
                    included: lineIncluded,
                    tax_ids: baseLine.tax_ids.map((tax) => tax.id),
                };
            });
            const round = (value) => roundPrecision(value, state.currency.rounding || 0.01);
            return {
                lines: result.map((line) => ({ ...line, excluded: round(line.excluded), included: round(line.included) })),
                excluded: round(excluded),
                included: round(included),
                taxes: round(included - excluded),
            };
        }

        /** Unit price before taxes from the customer's pricelist (list price without one). */
        function unitPrice(product, partner, quantity = 1) {
            return partner?.pricelist_id
                ? pricing.getPrice(partner.pricelist_id, product, quantity)
                : product.lst_price;
        }

        /** Price and discount of an order line, as Odoo would put them on the sale order line. */
        function linePrice(product, partner, quantity) {
            if (!partner?.pricelist_id) {
                return { price: product.lst_price, discount: 0 };
            }
            if (!discountEnabled) {
                return { price: unitPrice(product, partner, quantity), discount: 0 };
            }
            const { price, discount } = pricing.getPriceWithDiscount(partner.pricelist_id, product, quantity);
            // Stored with 2 decimals on the sale order line (Discount precision).
            return { price, discount: Math.round(discount * 100) / 100 };
        }

        function buildPricing(pricelists, items) {
            pricing = markRaw(new PricelistEngine(pricelists, items, state.categories));
        }

        function priceIncluded(product, partner) {
            return computeLines([{ product_id: product.id, price_unit: unitPrice(product, partner), quantity: 1 }], partner)
                .included;
        }

        async function refreshStorage() {
            const storage = browser.navigator.storage;
            if (storage?.estimate) {
                state.storage = await storage.estimate();
            }
            if (storage?.persisted) {
                state.persisted = await storage.persisted();
            }
        }

        async function loadLocal() {
            state.link = (await db.getMeta("link")) || null;
            state.lastSync = (await db.getMeta("lastSync")) || null;
            state.autoSend = Boolean(await db.getMeta("autoSend"));
            state.pin = (await db.getMeta("pin")) || false;
            state.currency = (await db.getMeta("currency")) || state.currency;
            const [company, taxes, positions, activities, categories, history, pricelists, pricelistItems] =
                await Promise.all([
                    db.getMeta("company"),
                    db.getMeta("taxes"),
                    db.getMeta("fiscalPositions"),
                    db.getMeta("activities"),
                    db.getMeta("categories"),
                    db.getMeta("history"),
                    db.getMeta("pricelists"),
                    db.getMeta("pricelistItems"),
                ]);
            state.warehouse = (await db.getMeta("warehouse")) || false;
            discountEnabled = Boolean(await db.getMeta("discountEnabled"));
            state.activities = markRaw(activities || []);
            state.categories = markRaw(categories || []);
            state.history = markRaw(history || []);
            const [partners, products, orders] = await Promise.all([
                db.getAll("partners"),
                db.getAll("products"),
                db.getAll("orders"),
            ]);
            partners.sort((a, b) => a.name.localeCompare(b.name));
            // Catalog arrays are raw: proxying thousands of records makes search slow.
            state.partners = markRaw(partners);
            state.products = markRaw(products);
            state.orders = Object.fromEntries(orders.map((order) => [order.uuid, order]));
            buildIndex();
            buildFiscal(company, taxes || [], positions || []);
            buildPricing(pricelists || [], pricelistItems || []);
            state.needsSync = Boolean(state.link) && (await db.getMeta("dataVersion")) !== DATA_VERSION;
        }

        async function readLinkFromUrl() {
            const hash = browser.location.hash;
            if (!hash.startsWith("#link=")) {
                return false;
            }
            browser.history.replaceState(null, "", APP_PATH);
            const link = JSON.parse(decodeURIComponent(hash.slice("#link=".length)));
            // Relinking with the same user keeps everything (pending orders included);
            // another user must not see nor send what the previous one loaded.
            const previous = state.link;
            // Links made before the uid was sent only carry the user name.
            const sameUser = previous && (previous.uid ? previous.uid === link.uid : previous.user === link.user);
            if (previous && !sameUser) {
                await resetLocal();
            }
            await db.setMeta("link", link);
            state.link = link;
            state.authExpired = false;
            if (sameUser && previous.key !== link.key) {
                // Renewed before expiring: the old key would stay valid until its date.
                revokeKey(previous.key);
            }
            if (browser.navigator.storage?.persist) {
                await browser.navigator.storage.persist();
            }
            return true;
        }

        async function sync() {
            if (!state.link || state.syncing) {
                return;
            }
            state.syncing = true;
            state.error = null;
            const started = performance.now();
            try {
                const response = await browser.fetch(`${APP_PATH}/api/sync`, {
                    method: "POST",
                    headers: { Authorization: `Bearer ${state.link.key}` },
                });
                if (response.status === 401) {
                    state.authExpired = true;
                    throw new Error(AUTH_EXPIRED_MESSAGE);
                }
                if (!response.ok) {
                    throw new Error(`Error del servidor (${response.status})`);
                }
                const data = await response.json();
                const downloaded = performance.now();
                data.partners.sort((a, b) => a.name.localeCompare(b.name));
                await db.replaceAll("partners", data.partners);
                await db.replaceAll("products", data.products);
                const lastSync = {
                    date: new Date().toISOString(),
                    partners: data.partners.length,
                    products: data.products.length,
                    activities: data.activities.length,
                    history: data.history.length,
                    downloadMs: Math.round(downloaded - started),
                    storeMs: Math.round(performance.now() - downloaded),
                };
                await db.setMeta("currency", data.currency);
                await db.setMeta("pin", data.pin || false);
                await db.setMeta("company", data.company);
                await db.setMeta("taxes", data.taxes);
                await db.setMeta("fiscalPositions", data.fiscal_positions);
                await db.setMeta("activities", data.activities);
                await db.setMeta("categories", data.categories);
                await db.setMeta("history", data.history);
                await db.setMeta("pricelists", data.pricelists);
                await db.setMeta("pricelistItems", data.pricelist_items);
                await db.setMeta("warehouse", data.warehouse);
                await db.setMeta("discountEnabled", data.discount_enabled);
                await db.setMeta("lastSync", lastSync);
                await db.setMeta("dataVersion", DATA_VERSION);
                state.partners = markRaw(data.partners);
                state.products = markRaw(data.products);
                state.activities = markRaw(data.activities);
                state.categories = markRaw(data.categories);
                state.history = markRaw(data.history);
                state.warehouse = data.warehouse;
                discountEnabled = data.discount_enabled;
                state.currency = data.currency;
                state.pin = data.pin || false;
                state.lastSync = lastSync;
                buildIndex();
                buildFiscal(data.company, data.taxes, data.fiscal_positions);
                buildPricing(data.pricelists, data.pricelist_items);
                await repriceDrafts();
                state.needsSync = false;
            } catch (error) {
                if (!state.authExpired) {
                    state.error = error.message || String(error);
                }
            } finally {
                state.syncing = false;
                refreshStorage();
            }
        }

        function linkDevice() {
            browser.location.href = `${APP_PATH}/link`;
        }

        function searchPartners(query, limit = 100) {
            const term = normalize(query);
            const result = [];
            for (const partner of state.partners) {
                if (!term || partner._search.includes(term)) {
                    result.push(partner);
                    if (result.length >= limit) {
                        break;
                    }
                }
            }
            return result;
        }

        function searchProducts(query, limit = 20) {
            const term = normalize(query);
            if (!term) {
                return [];
            }
            const result = [];
            for (const product of state.products) {
                if (product._search.includes(term)) {
                    result.push(product);
                    if (result.length >= limit) {
                        break;
                    }
                }
            }
            return result;
        }

        function findProductByCode(code) {
            return index.byCode.get((code || "").trim()) || null;
        }

        function getDraftOrder(partner, orders = state.orders) {
            return Object.values(orders).find(
                (order) => order.partner_id === partner.id && order.state === "draft"
            );
        }

        function newDraft(partner, activityId) {
            return {
                uuid: window.crypto.randomUUID(),
                kind: "order",
                partner_id: partner.id,
                partner_name: partner.name,
                date: new Date().toISOString(),
                state: "draft",
                activity_id: activityId || false,
                lines: [],
            };
        }

        async function saveDraft(order, partner) {
            // Prices follow the pricelist on every change: a rule may depend on the quantity.
            for (const line of order.lines) {
                const product = index.byId.get(line.product_id);
                if (product) {
                    const { price, discount } = linePrice(product, partner, line.quantity);
                    line.price_unit = price;
                    // The pricelist discount is a default: once the salesperson changes it, it stays.
                    if (!line.discount_edited) {
                        line.discount = discount;
                    }
                }
            }
            order.pricelist_id = partner.pricelist_id || false;
            const computed = computeLines(order.lines, partner);
            order.lines.forEach((orderLine, i) => (orderLine.tax_ids = computed.lines[i].tax_ids));
            order.fiscal_position_id = partner.fiscal_position_id || false;
            await saveOrder(order);
        }

        // Orders being built follow the prices and pricelists just synced.
        async function repriceDrafts() {
            const partners = new Map(state.partners.map((partner) => [partner.id, partner]));
            for (const draft of getOrdersByState("draft")) {
                const partner = partners.get(draft.partner_id);
                if (partner) {
                    await saveDraft(JSON.parse(JSON.stringify(draft)), partner);
                }
            }
        }

        /** Set the quantity of a product in the customer's draft (0 removes the line). */
        async function setQuantity(partner, product, quantity, activityId = false) {
            const current = getDraftOrder(partner);
            if (!current && !(quantity > 0)) {
                return;
            }
            const order = current ? JSON.parse(JSON.stringify(current)) : newDraft(partner, activityId);
            if (activityId && !order.activity_id) {
                order.activity_id = activityId;
            }
            const line = order.lines.find((l) => l.product_id === product.id);
            if (!(quantity > 0)) {
                order.lines = order.lines.filter((l) => l.product_id !== product.id);
            } else if (line) {
                line.quantity = quantity;
            } else {
                order.lines.unshift({
                    product_id: product.id,
                    name: product.display_name,
                    code: product.default_code || "",
                    quantity,
                    discount: 0,
                    price_unit: product.lst_price,
                });
            }
            await saveDraft(order, partner);
        }

        /** Discount in % on a line of the customer's draft. */
        async function setDiscount(partner, productId, discount) {
            const current = getDraftOrder(partner);
            const order = current && JSON.parse(JSON.stringify(current));
            const line = order?.lines.find((l) => l.product_id === productId);
            if (!line) {
                return;
            }
            line.discount = Math.min(Math.max(discount || 0, 0), 100);
            line.discount_edited = true;
            await saveDraft(order, partner);
        }

        function getLineQuantity(partner, productId, orders = state.orders) {
            const order = getDraftOrder(partner, orders);
            return order?.lines.find((line) => line.product_id === productId)?.quantity || 0;
        }

        async function addLine(partner, product, quantity, activityId = false) {
            const current = getLineQuantity(partner, product.id);
            await setQuantity(partner, product, current + quantity, activityId);
        }

        /**
         * Copy the lines of a previous order into the customer's draft, at today's
         * prices. Returns the names of the products no longer in the catalog.
         */
        async function repeatOrder(partner, lines, activityId = false) {
            const missing = [];
            for (const line of lines) {
                const product = index.byId.get(line.product_id);
                if (product) {
                    await addLine(partner, product, line.quantity, activityId);
                } else {
                    missing.push(line.name);
                }
            }
            return missing;
        }

        /** Close the visit without an order: it travels with the orders, as one more record. */
        async function registerNoPurchase(partner, activityId, reason) {
            const draft = getDraftOrder(partner);
            if (draft) {
                await db.delete("orders", draft.uuid);
                delete state.orders[draft.uuid];
            }
            const now = new Date().toISOString();
            await saveOrder({
                uuid: window.crypto.randomUUID(),
                kind: "no_purchase",
                partner_id: partner.id,
                partner_name: partner.name,
                activity_id: activityId,
                reason,
                date: now,
                closed_at: now,
                state: "ready",
                lines: [],
                location: await getLocation(),
            });
            if (state.autoSend) {
                sendOrders({ silent: true });
            }
        }

        // Number Odoo gave to an order sent from this device, once it came back in the history.
        function getServerName(uuid) {
            return state.history.find((order) => order.offline_uuid === uuid)?.name || false;
        }

        function getImageUrl(productId) {
            if (!imageUrls.has(productId)) {
                const promise = browser
                    .fetch(`${APP_PATH}/api/image/${productId}`, {
                        headers: { Authorization: `Bearer ${state.link.key}` },
                    })
                    .then((response) => (response.ok ? response.blob() : null))
                    .then((blob) => (blob ? URL.createObjectURL(blob) : null))
                    .catch(() => {
                        // Offline or failed: try again next time.
                        imageUrls.delete(productId);
                        return null;
                    });
                imageUrls.set(productId, promise);
            }
            return imageUrls.get(productId);
        }

        async function saveOrder(order) {
            await db.put("orders", JSON.parse(JSON.stringify(order)));
            state.orders[order.uuid] = order;
        }

        // Latest local order started from an activity, if any.
        function getActivityOrder(activityId, orders = state.orders) {
            return Object.values(orders)
                .filter((order) => order.activity_id === activityId)
                .sort((a, b) => b.date.localeCompare(a.date))[0];
        }

        // Components pass their own useState proxy of state.orders to stay reactive.
        function getOrdersByState(orderState, orders = state.orders) {
            return Object.values(orders)
                .filter((order) => order.state === orderState)
                .sort((a, b) => (b.sent_at || b.closed_at || b.date).localeCompare(a.sent_at || a.closed_at || a.date));
        }

        function getLocation() {
            const geolocation = browser.navigator.geolocation;
            if (!geolocation) {
                return Promise.resolve(null);
            }
            return new Promise((resolve) => {
                // The API timeout only starts once permission is granted: an unanswered
                // permission prompt must not block closing the order.
                browser.setTimeout(() => resolve(null), 8000);
                geolocation.getCurrentPosition(
                    ({ coords }) =>
                        // 0,0 with no accuracy is what emulators report: not a real position.
                        resolve(
                            !coords.latitude && !coords.longitude
                                ? null
                                : { latitude: coords.latitude, longitude: coords.longitude, accuracy: coords.accuracy }
                        ),
                    () => resolve(null),
                    { enableHighAccuracy: true, timeout: 5000, maximumAge: 60000 }
                );
            });
        }

        async function closeOrder(order, partner) {
            const totals = computeLines(order.lines, partner);
            order.lines.forEach((line, i) => {
                line.tax_ids = totals.lines[i].tax_ids;
                line.price_subtotal = totals.lines[i].excluded;
                line.price_total = totals.lines[i].included;
            });
            Object.assign(order, {
                state: "ready",
                closed_at: new Date().toISOString(),
                fiscal_position_id: partner.fiscal_position_id || false,
                amount_untaxed: totals.excluded,
                amount_tax: totals.taxes,
                amount_total: totals.included,
                location: await getLocation(),
            });
            await saveOrder(order);
            if (state.autoSend) {
                sendOrders({ silent: true });
            }
        }

        function buildPayload(order) {
            return {
                schema_version: ORDERS_SCHEMA_VERSION,
                kind: order.kind || "order",
                reason: order.reason || false,
                uuid: order.uuid,
                activity_id: order.activity_id || false,
                partner_id: order.partner_id,
                partner_name: order.partner_name,
                fiscal_position_id: order.fiscal_position_id,
                pricelist_id: order.pricelist_id || false,
                created_on_device: order.date,
                closed_at: order.closed_at,
                location: order.location,
                currency_id: state.currency.id,
                amount_untaxed: order.amount_untaxed,
                amount_tax: order.amount_tax,
                amount_total: order.amount_total,
                lines: order.lines.map((line) => ({
                    product_id: line.product_id,
                    name: line.name,
                    quantity: line.quantity,
                    price_unit: line.price_unit,
                    discount: line.discount || 0,
                    tax_ids: line.tax_ids,
                    price_subtotal: line.price_subtotal,
                    price_total: line.price_total,
                })),
            };
        }

        /**
         * Sends every closed order. An order is marked as sent only when Odoo
         * acknowledges its uuid; on any failure it stays ready and is resent later
         * (the server ignores duplicates).
         */
        async function sendOrders({ silent = false } = {}) {
            const ready = getOrdersByState("ready");
            if (!state.link || state.sending || !ready.length) {
                return;
            }
            state.sending = true;
            if (!silent) {
                state.error = null;
            }
            let sent = 0;
            try {
                for (let i = 0; i < ready.length; i += ORDERS_PER_REQUEST) {
                    const batch = ready.slice(i, i + ORDERS_PER_REQUEST);
                    const response = await browser.fetch(`${APP_PATH}/api/orders`, {
                        method: "POST",
                        headers: {
                            Authorization: `Bearer ${state.link.key}`,
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({ orders: batch.map(buildPayload) }),
                    });
                    if (response.status === 401) {
                        state.authExpired = true;
                    throw new Error(AUTH_EXPIRED_MESSAGE);
                    }
                    if (!response.ok) {
                        throw new Error(`Error del servidor al enviar pedidos (${response.status})`);
                    }
                    const result = await response.json();
                    const sentAt = new Date().toISOString();
                    const acknowledged = new Set([...result.accepted, ...result.duplicates]);
                    const rejected = new Map(result.rejected.map((item) => [item.uuid, item.reason]));
                    for (const order of batch) {
                        if (acknowledged.has(order.uuid)) {
                            await saveOrder({ ...order, state: "sent", sent_at: sentAt });
                            sent++;
                        } else if (rejected.has(order.uuid)) {
                            await saveOrder({ ...order, state: "rejected", reject_reason: rejected.get(order.uuid) });
                        }
                    }
                }
            } catch (error) {
                if (!silent && !state.authExpired) {
                    state.error = error.message || String(error);
                }
            } finally {
                state.sending = false;
                state.lastSend = { date: new Date().toISOString(), sent };
            }
        }

        async function setAutoSend(value) {
            state.autoSend = value;
            await db.setMeta("autoSend", value);
            if (value) {
                sendOrders({ silent: true });
            }
        }

        async function removeLine(order, productId) {
            if (order.state !== "draft") {
                return;
            }
            await saveOrder({ ...order, lines: order.lines.filter((line) => line.product_id !== productId) });
        }

        async function resetLocal() {
            await db.clearAll();
            Object.assign(state, {
                link: null,
                pin: false,
                locked: false,
                lastSync: null,
                error: null,
                needsSync: false,
                authExpired: false,
                autoSend: false,
                lastSend: null,
                partners: markRaw([]),
                products: markRaw([]),
                activities: markRaw([]),
                categories: markRaw([]),
                history: markRaw([]),
                warehouse: false,
                orders: {},
            });
            buildIndex();
            buildFiscal(null, [], []);
            buildPricing([], []);
            refreshStorage();
        }

        function daysToExpiry() {
            if (!state.link?.expiration) {
                return null;
            }
            return Math.ceil((new Date(state.link.expiration) - Date.now()) / 86400000);
        }

        /**
         * Revoke the API key in Odoo when online and wipe every local record, so
         * the next person linking this device starts from scratch.
         * Returns whether Odoo confirmed the revocation.
         */
        async function revokeKey(key) {
            try {
                const response = await browser.fetch(`${APP_PATH}/api/logout`, {
                    method: "POST",
                    headers: { Authorization: `Bearer ${key}` },
                });
                // 401: the key was already revoked or expired, nothing left to revoke.
                return response.ok || response.status === 401;
            } catch {
                return false;
            }
        }

        /**
         * Revoke the key, wipe the device and, when online, end the Odoo session and
         * go back to the Odoo login: the next person links the device with their user.
         */
        async function logout() {
            const revoked = await revokeKey(state.link.key);
            await resetLocal();
            if (revoked && browser.navigator.onLine) {
                browser.location.href = `/web/session/logout?redirect=${encodeURIComponent(`${APP_PATH}/link`)}`;
            }
            return revoked;
        }

        function unlock(pin) {
            if (pin === state.pin) {
                state.locked = false;
                return true;
            }
            return false;
        }

        function formatAmount(value) {
            const { symbol, position, digits } = state.currency;
            const amount = (value || 0).toLocaleString("es-AR", {
                minimumFractionDigits: digits,
                maximumFractionDigits: digits,
            });
            return position === "after" ? `${amount} ${symbol}` : `${symbol} ${amount}`;
        }

        function registerServiceWorker() {
            const serviceWorker = browser.navigator.serviceWorker;
            if (!serviceWorker) {
                return;
            }
            const hadController = Boolean(serviceWorker.controller);
            let reloading = false;
            serviceWorker.addEventListener("controllerchange", () => {
                // The first install also fires controllerchange (clients.claim): no reload then.
                if (hadController && !reloading) {
                    reloading = true;
                    browser.location.reload();
                }
            });
            serviceWorker.register(`${APP_PATH}/service-worker.js`, { scope: APP_PATH }).then((registration) => {
                // A version downloaded on a previous run is applied right away: orders are
                // already persisted, and a broken UI cannot block its own fix.
                if (registration.waiting && hadController) {
                    registration.waiting.postMessage("SKIP_WAITING");
                    return;
                }
                registration.addEventListener("updatefound", () => {
                    const installing = registration.installing;
                    installing?.addEventListener("statechange", () => {
                        if (installing.state === "installed" && hadController) {
                            waitingWorker = installing;
                            state.updateAvailable = true;
                        }
                    });
                });
                if (browser.navigator.onLine) {
                    registration.update().catch(() => {});
                }
            });
        }

        function applyUpdate() {
            waitingWorker?.postMessage("SKIP_WAITING");
        }

        browser.addEventListener("online", () => {
            state.online = true;
            if (state.autoSend) {
                sendOrders({ silent: true });
            }
        });
        // navigator.onLine is not reliable (captive portals, weak signal): keep retrying.
        browser.setInterval(() => {
            if (state.autoSend) {
                sendOrders({ silent: true });
            }
        }, AUTO_SEND_RETRY_MS);
        browser.addEventListener("offline", () => (state.online = false));

        await loadLocal();
        state.locked = Boolean(state.link && state.pin);
        let hiddenAt = null;
        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "hidden") {
                hiddenAt = Date.now();
            } else if (hiddenAt && Date.now() - hiddenAt > RELOCK_AFTER_MS && state.link && state.pin) {
                state.locked = true;
            }
        });
        const justLinked = await readLinkFromUrl();
        registerServiceWorker();
        refreshStorage();
        if (justLinked || (state.needsSync && browser.navigator.onLine)) {
            sync();
        }
        if (state.autoSend) {
            sendOrders({ silent: true });
        }

        return {
            state,
            sync,
            linkDevice,
            searchPartners,
            searchProducts,
            findProductByCode,
            getDraftOrder,
            addLine,
            formatAmount,
            applyUpdate,
            computeLines,
            priceIncluded,
            closeOrder,
            removeLine,
            logout,
            unlock,
            daysToExpiry,
            sendOrders,
            setAutoSend,
            getOrdersByState,
            getActivityOrder,
            setQuantity,
            setDiscount,
            unitPrice,
            getLineQuantity,
            repeatOrder,
            registerNoPurchase,
            getServerName,
            getImageUrl,
            getCategoryChildren,
            getCategoryProducts,
            getCategoryCount,
        };
    },
};

registry.category("services").add("preventa", preventaService);
