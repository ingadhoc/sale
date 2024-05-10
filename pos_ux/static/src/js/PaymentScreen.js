/** @odoo-module **/

import PaymentScreen from 'point_of_sale.PaymentScreen';
import Registries from 'point_of_sale.Registries';

export const PosUxPaymentScreen = (PaymentScreen) =>
    class extends PaymentScreen {
        shouldDownloadInvoice() {
            if (this.env.pos.config.block_invoice_download) {
                return false;
            } else {
                return super.shouldDownloadInvoice();
            }
        }
    };

Registries.Component.extend(PaymentScreen, PosUxPaymentScreen);
