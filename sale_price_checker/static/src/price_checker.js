/** @odoo-module **/

import { Component, onWillUnmount, useExternalListener, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Interaction } from "@web/public/interaction";

class PriceChecker extends Component {
    static template = "sale_price_checker.PriceChecker";
    static props = {};

    setup() {
        this.state = useState({
            mode: "idle",
            barcode: "",
            product: null,
            lastBarcode: "",
            history: [],
        });
        this.resetTimer = null;
        this.companyId = window.priceCheckerConfig.companyId;
        this.pricelistId = window.priceCheckerConfig.pricelistId;

        const barcode = useService("barcode");
        useExternalListener(barcode.bus, "barcode_scanned", (ev) => {
            this.state.barcode = ev.detail.barcode;
            this.lookup(ev.detail.barcode);
        });
        onWillUnmount(() => this.clearResetTimer());
    }

    clearResetTimer() {
        if (this.resetTimer) {
            clearTimeout(this.resetTimer);
            this.resetTimer = null;
        }
    }

    scheduleReset() {
        this.clearResetTimer();
        this.resetTimer = setTimeout(() => this.reset(), 5000);
    }

    reset() {
        this.state.mode = "idle";
        this.state.barcode = "";
        this.state.product = null;
        this.state.lastBarcode = "";
    }

    pushHistory(product) {
        const next = this.state.history.filter((p) => p.image_url !== product.image_url);
        next.unshift(product);
        this.state.history = next.slice(0, 5);
    }

    onSubmit() {
        this.lookup((this.state.barcode || "").trim());
    }

    async lookup(barcode) {
        if (!barcode) {
            return;
        }
        this.state.mode = "loading";
        this.state.lastBarcode = barcode;
        try {
            const params = { barcode };
            if (this.pricelistId) {
                params.pricelist_id = this.pricelistId;
            }
            const response = await fetch(`/price-checker/${this.companyId}/lookup`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params,
                }),
            });
            const data = await response.json();
            const result = data.result || { found: false };
            if (result.found) {
                this.state.product = result;
                this.state.mode = "showing";
                this.pushHistory(result);
            } else {
                this.state.mode = "not_found";
            }
        } catch (_err) {
            this.state.mode = "not_found";
        }
        this.scheduleReset();
    }
}

class PriceCheckerInteraction extends Interaction {
    static selector = "#price_checker_root";

    setup() {
        this.mountComponent(this.el, PriceChecker);
    }
}

registry.category("public.interactions").add(
    "sale_price_checker.price_checker",
    PriceCheckerInteraction,
);
