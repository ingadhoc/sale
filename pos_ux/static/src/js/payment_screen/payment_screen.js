import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";

patch(OrderPaymentValidation.prototype, {
    shouldDownloadInvoice() {
        if (this.pos.config.block_invoice_download || this.pos.session.invoice_contingency) {
            return false;
        }
        return super.shouldDownloadInvoice(...arguments);
    },
});
