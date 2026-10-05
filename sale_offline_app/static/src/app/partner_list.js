import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PartnerList extends Component {
    static template = "sale_offline_app.PartnerList";
    static props = { onSelect: Function };

    setup() {
        this.preventa = useService("preventa");
        this.data = useState(this.preventa.state);
        this.state = useState({ query: "" });
    }

    subtitle(partner) {
        return [partner.vat, partner.city].filter(Boolean).join(" · ");
    }

    get partners() {
        return this.preventa.searchPartners(this.state.query);
    }
}
