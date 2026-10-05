import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class OrdersScreen extends Component {
    static template = "sale_offline_app.OrdersScreen";
    static props = { onOpenOrder: Function };

    setup() {
        this.preventa = useService("preventa");
        this.data = useState(this.preventa.state);
    }

    get sections() {
        const byState = (orderState) => this.preventa.getOrdersByState(orderState, this.data.orders);
        return [
            { key: "ready", title: "Listos para enviar", orders: byState("ready") },
            { key: "rejected", title: "Rechazados por Odoo", orders: byState("rejected") },
            { key: "sent", title: "Enviados", orders: byState("sent") },
            { key: "draft", title: "En carga", orders: byState("draft") },
        ].filter((section) => section.orders.length);
    }

    get readyCount() {
        return this.preventa.getOrdersByState("ready", this.data.orders).length;
    }

    formatDate(iso) {
        return iso ? new Date(iso).toLocaleString("es-AR", { hourCycle: "h23" }) : "";
    }

    orderInfo(order) {
        const parts = [`${order.lines.length} líneas`];
        if (order.amount_total !== undefined) {
            parts.push(this.preventa.formatAmount(order.amount_total));
        }
        if (order.state === "sent") {
            parts.push(`enviado ${this.formatDate(order.sent_at)}`);
        } else if (order.closed_at) {
            parts.push(`cerrado ${this.formatDate(order.closed_at)}`);
        }
        return parts.join(" · ");
    }

    onToggleAutoSend(ev) {
        this.preventa.setAutoSend(ev.target.checked);
    }
}
