import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    getDefaultPartnerId() {
        return this.config.default_order_partner_id?.id || super.getDefaultPartnerId();
    },

    // Core only sets the default partner on a brand new order, so an empty one
    // reused from a previous session would open without it.
    getEmptyOrder() {
        const order = super.getEmptyOrder(...arguments);
        if (order && !order.partner_id) {
            order.partner_id = this.getDefaultPartnerId();
        }
        return order;
    },
});
