import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const STATE_LABELS = {
    ready: "Listo para enviar",
    sent: "Enviado",
    rejected: "Rechazado por Odoo",
};

export class OrderDetail extends Component {
    static template = "sale_offline_app.OrderDetail";
    static props = { uuid: String };

    setup() {
        this.preventa = useService("preventa");
        this.data = useState(this.preventa.state);
    }

    get order() {
        return this.data.orders[this.props.uuid];
    }

    get stateLabel() {
        return STATE_LABELS[this.order.state] || this.order.state;
    }

    get mapsUrl() {
        const location = this.order.location;
        return location && `https://www.google.com/maps/search/?api=1&query=${location.latitude},${location.longitude}`;
    }

    formatDate(iso) {
        return iso ? new Date(iso).toLocaleString("es-AR", { hourCycle: "h23" }) : "";
    }
}
