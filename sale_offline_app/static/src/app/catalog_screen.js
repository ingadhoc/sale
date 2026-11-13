import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ProductImage } from "./product_image";

const SEARCH_LIMIT = 50;

/** One product of the catalog, with − / + when an order is being built. */
export class CatalogProduct extends Component {
    static template = "sale_offline_app.CatalogProduct";
    static props = {
        product: Object,
        partner: { type: [Object, Boolean], optional: true },
        activityId: { type: [Number, Boolean], optional: true },
    };
    static components = { ProductImage };

    setup() {
        this.preventa = useService("preventa");
        this.data = useState(this.preventa.state);
    }

    get quantity() {
        return this.props.partner
            ? this.preventa.getLineQuantity(this.props.partner, this.props.product.id, this.data.orders)
            : 0;
    }

    get price() {
        return this.preventa.formatAmount(this.preventa.priceIncluded(this.props.product, this.props.partner));
    }

    get discount() {
        if (!this.props.partner) {
            return 0;
        }
        const order = this.preventa.getDraftOrder(this.props.partner, this.data.orders);
        return order?.lines.find((line) => line.product_id === this.props.product.id)?.discount || 0;
    }

    onDiscount(ev) {
        this.preventa.setDiscount(this.props.partner, this.props.product.id, parseFloat(ev.target.value) || 0);
    }

    get stock() {
        return this.props.product.free_qty;
    }

    setQuantity(quantity) {
        const { partner, product, activityId } = this.props;
        this.preventa.setQuantity(partner, product, Math.max(quantity, 0), activityId);
    }

    onInput(ev) {
        const quantity = parseFloat(ev.target.value);
        this.setQuantity(quantity > 0 ? quantity : 0);
    }
}

/** A category of the accordion: its subcategories, then its own products. */
export class CatalogNode extends Component {
    static template = "sale_offline_app.CatalogNode";
    static props = {
        category: Object,
        depth: Number,
        partner: { type: [Object, Boolean], optional: true },
        activityId: { type: [Number, Boolean], optional: true },
    };
    static components = { CatalogProduct };

    setup() {
        this.preventa = useService("preventa");
        this.state = useState({ open: false });
    }

    get children() {
        return this.preventa.getCategoryChildren(this.props.category.id);
    }

    get products() {
        return this.preventa.getCategoryProducts(this.props.category.id);
    }

    get count() {
        return this.preventa.getCategoryCount(this.props.category.id);
    }
}
// Recursive: a category renders its subcategories with the same component.
CatalogNode.components = { ...CatalogNode.components, CatalogNode };

export class CatalogScreen extends Component {
    static template = "sale_offline_app.CatalogScreen";
    static props = {
        partner: { type: [Object, Boolean], optional: true },
        activityId: { type: [Number, Boolean], optional: true },
        onShowOrder: { type: Function, optional: true },
    };
    static components = { CatalogNode, CatalogProduct };

    setup() {
        this.preventa = useService("preventa");
        this.data = useState(this.preventa.state);
        this.state = useState({ query: "" });
    }

    get roots() {
        // Read through the reactive state so a sync rebuilds the tree on screen.
        return this.data.categories && this.preventa.getCategoryChildren(false);
    }

    get uncategorized() {
        return this.preventa.getCategoryProducts(false);
    }

    get results() {
        return this.preventa.searchProducts(this.state.query, SEARCH_LIMIT);
    }

    /** What is being ordered so far, for the bar at the bottom. */
    get summary() {
        const order = this.props.partner && this.preventa.getDraftOrder(this.props.partner, this.data.orders);
        if (!order?.lines.length) {
            return false;
        }
        const totals = this.preventa.computeLines(order.lines, this.props.partner);
        return { count: order.lines.length, total: this.preventa.formatAmount(totals.included) };
    }
}
