import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    getDefaultPartnerId() {
        return this.config.default_order_partner_id?.id || super.getDefaultPartnerId();
    },
});
