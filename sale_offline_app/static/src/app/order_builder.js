import { Component, useRef, useState } from "@odoo/owl";
import { scanBarcode } from "@web/core/barcode/barcode_dialog";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useBus, useService } from "@web/core/utils/hooks";

export class OrderBuilder extends Component {
    static template = "sale_offline_app.OrderBuilder";
    static props = { partner: Object, activityId: { type: [Number, Boolean], optional: true } };

    setup() {
        this.preventa = useService("preventa");
        this.notification = useService("notification");
        this.data = useState(this.preventa.state);
        this.state = useState({ query: "", product: null, quantity: 1 });
        this.searchRef = useRef("search");
        this.cameraSupported = isBarcodeScannerSupported();
        // Hardware scanners when the focus is not on an input; inside the search
        // input the scan arrives as typed text followed by Enter.
        useBus(useService("barcode").bus, "barcode_scanned", (ev) => this.onCode(ev.detail.barcode));
    }

    get order() {
        // Read through the component's reactive state so it re-renders on changes.
        return this.preventa.getDraftOrder(this.props.partner, this.data.orders);
    }

    get activity() {
        const activityId = this.order?.activity_id || this.props.activityId;
        return activityId && this.data.activities.find((activity) => activity.id === activityId);
    }

    get suggestions() {
        if (this.state.product) {
            return [];
        }
        return this.preventa.searchProducts(this.state.query);
    }

    get totals() {
        return this.preventa.computeLines(this.order?.lines || [], this.props.partner);
    }

    productHint(product) {
        const price = this.preventa.priceIncluded(product, this.props.partner);
        return [product.default_code, product.barcode, `${this.preventa.formatAmount(price)} c/imp.`]
            .filter(Boolean)
            .join(" · ");
    }

    select(product) {
        this.state.product = product;
        this.state.query = product.display_name;
        this.state.quantity = 1;
    }

    clear() {
        this.state.product = null;
        this.state.query = "";
        this.state.quantity = 1;
        this.searchRef.el?.focus();
    }

    onCode(code) {
        const product = this.preventa.findProductByCode(code);
        if (product) {
            this.select(product);
        } else {
            this.notification.add(`No hay un producto con el código ${code}`, { type: "warning" });
        }
    }

    onSearchInput() {
        this.state.product = null;
    }

    onSearchKeydown(ev) {
        if (ev.key !== "Enter") {
            return;
        }
        ev.preventDefault();
        const product = this.preventa.findProductByCode(this.state.query);
        if (product) {
            this.select(product);
        } else if (this.suggestions.length === 1) {
            this.select(this.suggestions[0]);
        }
    }

    async onCamera() {
        try {
            const code = await scanBarcode(this.env);
            if (code) {
                this.onCode(code);
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
    }

    async removeLine(line) {
        await this.preventa.removeLine(this.order, line.product_id);
    }

    closeOrder() {
        const order = this.order;
        this.env.services.dialog.add(ConfirmationDialog, {
            title: "Cerrar pedido",
            body: `Después de cerrarlo no se puede modificar. Total: ${this.preventa.formatAmount(this.totals.included)}`,
            confirmLabel: "Cerrar pedido",
            cancelLabel: "Seguir cargando",
            confirm: async () => {
                await this.preventa.closeOrder(order, this.props.partner);
                this.notification.add("Pedido cerrado: queda listo para enviar.", { type: "success" });
            },
            cancel: () => {},
        });
    }

    async add() {
        const quantity = parseFloat(this.state.quantity);
        if (!this.state.product || !(quantity > 0)) {
            return;
        }
        await this.preventa.addLine(this.props.partner, this.state.product, quantity, this.props.activityId);
        this.clear();
    }
}
