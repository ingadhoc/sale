import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Two views of the same orders:
 * - "send": what is waiting to go to Odoo, with the send button;
 * - "orders": orders being built, sent from this device and the history from Odoo.
 */
export class OrdersScreen extends Component {
    static template = "sale_offline_app.OrdersScreen";
    static props = { mode: String, onOpenOrder: Function, onOpenHistory: Function };

    setup() {
        this.preventa = useService("preventa");
        this.data = useState(this.preventa.state);
    }

    /** Ids of the customers matching the search (code, VAT or name), or false without one. */
    get partnerIds() {
        // The send view has no search box: a query typed in Pedidos must not filter it.
        return (
            this.props.mode === "orders" &&
            this.data.ordersQuery &&
            new Set(this.preventa.searchPartners(this.data.ordersQuery, Infinity).map((partner) => partner.id))
        );
    }

    get sections() {
        const partnerIds = this.partnerIds;
        const byState = (orderState) =>
            this.preventa
                .getOrdersByState(orderState, this.data.orders)
                .filter((order) => !partnerIds || partnerIds.has(order.partner_id));
        const sections =
            this.props.mode === "send"
                ? [
                      { key: "ready", title: "Sin enviar", orders: byState("ready") },
                      { key: "rejected", title: "Rechazados por Odoo", orders: byState("rejected") },
                  ]
                : [
                      { key: "draft", title: "En carga", orders: byState("draft") },
                      { key: "sent", title: "Enviados desde este celular", orders: byState("sent") },
                  ];
        return sections.filter((section) => section.orders.length);
    }

    get history() {
        // Orders sent from this device are already listed above.
        const local = new Set(Object.keys(this.data.orders));
        const partnerIds = this.partnerIds;
        return this.data.history.filter(
            (order) => !local.has(order.offline_uuid) && (!partnerIds || partnerIds.has(order.partner_id))
        );
    }

    get readyCount() {
        return this.preventa.getOrdersByState("ready", this.data.orders).length;
    }

    formatDate(iso) {
        return iso ? new Date(iso).toLocaleString("es-AR", { hourCycle: "h23" }) : "";
    }

    orderInfo(order) {
        if (order.kind === "no_purchase") {
            return [`No compra: ${order.reason}`, this.formatDate(order.sent_at || order.closed_at)].join(" · ");
        }
        const parts = [`${order.lines.length} líneas`];
        if (order.amount_total !== undefined) {
            parts.push(this.preventa.formatAmount(order.amount_total));
        }
        const serverName = order.state === "sent" && this.preventa.getServerName(order.uuid);
        if (serverName) {
            parts.push(serverName);
        }
        if (order.state === "sent") {
            parts.push(`enviado ${this.formatDate(order.sent_at)}`);
        } else if (order.closed_at) {
            parts.push(`cerrado ${this.formatDate(order.closed_at)}`);
        }
        return parts.join(" · ");
    }

    historyInfo(order) {
        return [order.name, this.formatDate(order.date_order), this.preventa.formatAmount(order.amount_total)].join(
            " · "
        );
    }
}
