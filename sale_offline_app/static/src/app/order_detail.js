import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const STATE_LABELS = {
    ready: "Listo para enviar",
    sent: "Enviado",
    rejected: "Rechazado por Odoo",
};

/** Read-only view of an order: one from this device, or one of the history from Odoo. */
export class OrderDetail extends Component {
    static template = "sale_offline_app.OrderDetail";
    static props = { order: Object, fromHistory: Boolean, onRepeat: Function };

    setup() {
        this.preventa = useService("preventa");
        this.data = useState(this.preventa.state);
    }

    get order() {
        return this.props.order;
    }

    get isNoPurchase() {
        return this.order.kind === "no_purchase";
    }

    get stateLabel() {
        if (this.props.fromHistory) {
            return this.order.name;
        }
        if (this.isNoPurchase) {
            return `No compra · ${STATE_LABELS[this.order.state] || this.order.state}`;
        }
        const label = STATE_LABELS[this.order.state] || this.order.state;
        const serverName = this.preventa.getServerName(this.order.uuid);
        return serverName ? `${label} · ${serverName}` : label;
    }

    get mapsUrl() {
        const location = this.order.location;
        return location && `https://www.google.com/maps/search/?api=1&query=${location.latitude},${location.longitude}`;
    }

    get canRepeat() {
        return !this.isNoPurchase && this.order.lines.length > 0;
    }

    lineTotal(line) {
        return line.price_total ?? line.price_unit * line.quantity;
    }

    formatDate(iso) {
        return iso ? new Date(iso).toLocaleString("es-AR", { hourCycle: "h23" }) : "";
    }
}
