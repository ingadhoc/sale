import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(...arguments);
        if (this.config.billing_behavior !== 'on_demand') {
            this.to_invoice = true;
        }
    },
});
