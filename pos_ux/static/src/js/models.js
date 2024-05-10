odoo.define('pos_ux.models', function (require) {
    "use strict";

var { PosGlobalState, Order } = require('point_of_sale.models');
var { Gui } = require('point_of_sale.Gui');
const Registries = require('point_of_sale.Registries');

const PosUxPosGlobalState = (PosGlobalState) => class PosUxPosGlobalState extends PosGlobalState {

    async setContingencyMode(){
        let confirmText = this.env.pos.pos_session.invoice_contingency ? this.env._t('End contingecy'):  this.env._t('Set contingecy');
        let reason = this.env._t('If you enter the contingency mode, invoices will never be created.');

        const { confirmed } =  await Gui.showPopup('ConfirmPopup', {
            title: this.env._t('Change contingency mode'),
            body: reason,
            confirmText: confirmText,
            cancelText: this.env._t('Close'),
        });
        if (confirmed){
            const contingency_state = await this.env.services.rpc({
                model: 'pos.session',
                method: 'pos_toogle_contingency_mode',
                args: [odoo.pos_session_id],
            });
            this.env.pos.pos_session.invoice_contingency = contingency_state;
        }

    }
}
Registries.Model.extend(PosGlobalState, PosUxPosGlobalState);

const PosUxOrder = (Order) => class PosUxOrder extends Order {
    constructor(obj, options) {
        super(...arguments);
        if (this.pos.config.billing_behavior !== 'on_demand') {
            this.to_invoice = true;
        }
    }
}
Registries.Model.extend(Order, PosUxOrder);

});
