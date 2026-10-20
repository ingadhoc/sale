import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const WEEKDAYS = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
const OVERDUE = "overdue";

function localDate(offsetDays = 0) {
    const now = new Date();
    now.setDate(now.getDate() + offsetDays);
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

export class ActivitiesScreen extends Component {
    static template = "sale_offline_app.ActivitiesScreen";
    static props = { onStart: Function };

    setup() {
        this.preventa = useService("preventa");
        this.data = useState(this.preventa.state);
        this.state = useState({ query: "" });
    }

    /** One chip per synced day, plus "Atrasadas" when there are overdue visits. */
    get days() {
        const today = localDate();
        const tomorrow = localDate(1);
        const dates = [...new Set(this.data.activities.map((activity) => activity.date_deadline))].sort();
        const days = [];
        if (dates.some((date) => date < today)) {
            days.push({ key: OVERDUE, label: "Atrasadas" });
        }
        for (const date of dates.filter((date) => date >= today)) {
            const [year, month, day] = date.split("-");
            let label = `${WEEKDAYS[new Date(year, month - 1, day).getDay()]} ${day}/${month}`;
            if (date === today) {
                label = "Hoy";
            } else if (date === tomorrow) {
                label = "Mañana";
            }
            days.push({ key: date, label });
        }
        return days;
    }

    get selectedDay() {
        const keys = this.days.map((day) => day.key);
        if (keys.includes(this.data.workDay)) {
            return this.data.workDay;
        }
        const today = localDate();
        return keys.includes(today) ? today : keys.find((key) => key !== OVERDUE) || keys[0];
    }

    get items() {
        const today = localDate();
        const day = this.selectedDay;
        const partners = new Map(this.data.partners.map((partner) => [partner.id, partner]));
        // A search looks through every synced day, not only the one selected.
        const matches =
            this.state.query &&
            new Set(this.preventa.searchPartners(this.state.query, Infinity).map((partner) => partner.id));
        return this.data.activities
            .filter((activity) =>
                matches
                    ? matches.has(activity.partner_id)
                    : day === OVERDUE
                      ? activity.date_deadline < today
                      : activity.date_deadline === day
            )
            .map((activity) => ({
                activity,
                partner: partners.get(activity.partner_id),
                order: this.preventa.getActivityOrder(activity.id, this.data.orders),
            }));
    }

    get doneCount() {
        return this.items.filter((item) => item.order && item.order.state !== "draft").length;
    }

    /** Color by kind of action (order or no purchase), check and time once sent. */
    badge(order) {
        if (!order) {
            return false;
        }
        if (order.state === "draft") {
            return { label: "En carga", cls: "text-bg-warning", icon: "fa-pencil" };
        }
        const noPurchase = order.kind === "no_purchase";
        const label = noPurchase ? "No compra" : "Pedido";
        const cls = order.state === "rejected" ? "text-bg-dark" : noPurchase ? "text-bg-danger" : "text-bg-primary";
        if (order.state === "sent") {
            const time = new Date(order.sent_at).toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
            return { label: `${label} ${time}`, cls, icon: "fa-check" };
        }
        return { label, cls, icon: order.state === "rejected" ? "fa-exclamation-triangle" : "fa-clock-o" };
    }

    title(item) {
        if (!item.partner) {
            return "Cliente no disponible";
        }
        return item.partner.ref ? `${item.partner.ref} - ${item.partner.name}` : item.partner.name;
    }

    subtitle(item) {
        const partner = item.partner || {};
        const address = [partner.street, partner.city].filter(Boolean).join(", ");
        if (!this.state.query) {
            return address;
        }
        const [year, month, day] = item.activity.date_deadline.split("-");
        return [`${day}/${month}`, address].filter(Boolean).join(" · ");
    }

    /** Google Maps on the customer: its coordinates, else its address. */
    mapsUrl(partner) {
        if (!partner) {
            return false;
        }
        const { partner_latitude: lat, partner_longitude: lng } = partner;
        const query =
            lat || lng
                ? `${lat},${lng}`
                : [partner.street, partner.city, partner.state_id, partner.country_id].filter(Boolean).join(", ");
        return query && `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
    }
}
