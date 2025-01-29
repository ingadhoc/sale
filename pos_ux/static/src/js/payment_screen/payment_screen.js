/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    shouldDownloadInvoice() {
        if (this.pos.config.block_invoice_download || this.pos.pos_session.invoice_contingency) {
            return false;
        } else {
            return super.shouldDownloadInvoice();
        }
    },
});
