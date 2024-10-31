/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.pos.config.billing_behavior !== 'on_demand') {
            this.to_invoice = true;
        }
    },
});
