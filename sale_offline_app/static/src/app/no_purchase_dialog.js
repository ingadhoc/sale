import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

/** Asks for the reason of a visit without an order. Free text for now. */
export class NoPurchaseDialog extends Component {
    static template = "sale_offline_app.NoPurchaseDialog";
    static components = { Dialog };
    static props = { partnerName: String, confirm: Function, close: Function };

    setup() {
        this.state = useState({ reason: "" });
    }

    async confirm() {
        const reason = this.state.reason.trim();
        if (!reason) {
            return;
        }
        await this.props.confirm(reason);
        this.props.close();
    }
}
