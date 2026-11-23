import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { partnerTitle } from "./utils";

export class PartnerList extends Component {
    static template = "sale_offline_app.PartnerList";
    static props = { onSelect: Function };

    setup() {
        this.preventa = useService("preventa");
        this.data = useState(this.preventa.state);
        this.partnerTitle = partnerTitle;
        this.state = useState({ query: "" });
    }

    subtitle(partner) {
        return [partner.vat, partner.street, partner.city].filter(Boolean).join(" · ");
    }

    get partners() {
        return this.preventa.searchPartners(this.state.query);
    }
}
