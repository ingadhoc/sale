
/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";


patch(Navbar.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },

    async setContingencyMode(){
        let confirmText = this.pos.pos_session.invoice_contingency ? _t('End contingecy'):  _t('Set contingecy');
        let reason = _t('If you enter the contingency mode, invoices will never be created.');

        const { confirmed } = await this.popup.add(ConfirmPopup, {
            title: _t('Change contingency mode'),
            body: reason,
            confirmText: confirmText,
            cancelText: _t('Close'),
        });

        if (confirmed){
            const contingency_state = await this.orm.call('pos.session','pos_toogle_contingency_mode',[odoo.pos_session_id],{});
            this.pos.pos_session.invoice_contingency = contingency_state;
        }

    }
});
