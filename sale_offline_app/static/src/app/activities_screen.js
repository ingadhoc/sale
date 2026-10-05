import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const ORDER_STATE_LABELS = {
    draft: ["En carga", "text-bg-warning"],
    ready: ["Pedido cerrado", "text-bg-primary"],
    sent: ["Pedido enviado", "text-bg-success"],
    rejected: ["Rechazado", "text-bg-danger"],
};

function localToday() {
    const now = new Date();
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

export class ActivitiesScreen extends Component {
    static template = "sale_offline_app.ActivitiesScreen";
    static props = { onStart: Function };

    setup() {
        this.preventa = useService("preventa");
        this.data = useState(this.preventa.state);
    }

    get sections() {
        const today = localToday();
        const partners = new Map(this.data.partners.map((partner) => [partner.id, partner]));
        const items = this.data.activities.map((activity) => ({
            activity,
            partner: partners.get(activity.partner_id),
            order: this.preventa.getActivityOrder(activity.id, this.data.orders),
        }));
        return [
            { key: "overdue", title: "Atrasadas", items: items.filter((i) => i.activity.date_deadline < today) },
            { key: "today", title: "Hoy", items: items.filter((i) => i.activity.date_deadline === today) },
            { key: "next", title: "Próximos días", items: items.filter((i) => i.activity.date_deadline > today) },
        ].filter((section) => section.items.length);
    }

    orderBadge(order) {
        return order && ORDER_STATE_LABELS[order.state];
    }

    formatDate(isoDate) {
        const [year, month, day] = isoDate.split("-");
        return `${day}/${month}/${year}`;
    }

    subtitle(item) {
        return [item.partner?.city, this.formatDate(item.activity.date_deadline)].filter(Boolean).join(" · ");
    }
}
