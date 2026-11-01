import { roundPrecision } from "@web/core/utils/numbers";

// Guards against pricelists based on each other in a loop.
const MAX_DEPTH = 10;

function utcNow() {
    // Same format Odoo sends rule dates in ("YYYY-MM-DD HH:MM:SS", UTC), so strings compare.
    return new Date().toISOString().slice(0, 19).replace("T", " ");
}

/**
 * Pricelist engine of the app: mirrors product.pricelist._compute_price_rule and
 * product.pricelist.item._compute_price for a product in its own UoM.
 * Currency conversion between pricelists is not handled: every pricelist is
 * assumed to be in the company currency.
 */
export class PricelistEngine {
    constructor(pricelists = [], items = [], categories = []) {
        this.itemsByPricelist = new Map(pricelists.map((pricelist) => [pricelist.id, []]));
        // Items arrive in the order Odoo tries them: keep it.
        for (const item of items) {
            this.itemsByPricelist.get(item.pricelist_id)?.push(item);
        }
        this.parentById = new Map(categories.map((category) => [category.id, category.parent_id]));
    }

    _inCategory(product, categId) {
        for (let id = product.categ_id; id; id = this.parentById.get(id)) {
            if (id === categId) {
                return true;
            }
        }
        return false;
    }

    _isApplicable(item, product, quantity, now) {
        if ((item.date_start && item.date_start > now) || (item.date_end && item.date_end < now)) {
            return false;
        }
        if (item.min_quantity && quantity < item.min_quantity) {
            return false;
        }
        switch (item.applied_on) {
            case "2_product_category":
                return this._inCategory(product, item.categ_id);
            case "1_product":
                return product.product_tmpl_id === item.product_tmpl_id;
            case "0_product_variant":
                return product.id === item.product_id;
            default:
                return true;
        }
    }

    _basePrice(item, product, quantity, now, depth) {
        if (item.base === "pricelist" && item.base_pricelist_id) {
            return this.getPrice(item.base_pricelist_id, product, quantity, now, depth + 1);
        }
        return item.base === "standard_price" ? product.standard_price || 0 : product.lst_price;
    }

    _rule(pricelistId, product, quantity, now) {
        const items = this.itemsByPricelist.get(pricelistId);
        return items?.find((i) => this._isApplicable(i, product, quantity, now)) || false;
    }

    /** Unit price of the product for that pricelist and quantity, before taxes. */
    getPrice(pricelistId, product, quantity = 1, now = utcNow(), depth = 0) {
        const item = depth < MAX_DEPTH && this._rule(pricelistId, product, quantity, now);
        if (!item) {
            return product.lst_price;
        }
        if (item.compute_price === "fixed") {
            return item.fixed_price;
        }
        const base = this._basePrice(item, product, quantity, now, depth);
        if (item.compute_price === "percentage") {
            return base - base * (item.percent_price / 100) || 0;
        }
        // Formula.
        const discount = item.base !== "standard_price" ? item.price_discount : -item.price_markup;
        let price = base - base * (discount / 100);
        if (item.price_round) {
            price = roundPrecision(price, item.price_round);
        }
        if (item.price_surcharge) {
            price += item.price_surcharge;
        }
        if (item.price_min_margin) {
            price = Math.max(price, base + item.price_min_margin);
        }
        if (item.price_max_margin) {
            price = Math.min(price, base + item.price_max_margin);
        }
        return price;
    }

    /**
     * Price split the way sale.order.line shows it: when the rule is a percentage
     * (_show_discount), the price before the discount and the discount in %.
     * Mirrors product.pricelist.item._compute_price_before_discount.
     */
    getPriceWithDiscount(pricelistId, product, quantity = 1) {
        const now = utcNow();
        const price = this.getPrice(pricelistId, product, quantity, now);
        let item = this._rule(pricelistId, product, quantity, now);
        if (!item || item.compute_price !== "percentage") {
            return { price, discount: 0 };
        }
        for (let depth = 0; item.base === "pricelist" && depth < MAX_DEPTH; depth++) {
            const baseRule = this._rule(item.base_pricelist_id, product, quantity, now);
            if (!baseRule || baseRule.compute_price !== "percentage") {
                break;
            }
            item = baseRule;
        }
        const base = this._basePrice(item, product, quantity, now, 0);
        const discount = base ? ((base - price) / base) * 100 : 0;
        // Only a positive discount is shown: a surcharge stays in the price.
        return (discount > 0 && base > 0) || (discount < 0 && base < 0)
            ? { price: base, discount }
            : { price, discount: 0 };
    }
}
