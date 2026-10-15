import { Component, useState } from "@odoo/owl";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useService } from "@web/core/utils/hooks";
import { ActivitiesScreen } from "./activities_screen";
import { CatalogScreen } from "./catalog_screen";
import { LockScreen } from "./lock_screen";
import { OrderBuilder } from "./order_builder";
import { KEY_EXPIRY_WARNING_DAYS } from "./preventa_service";
import { OrderDetail } from "./order_detail";
import { OrdersScreen } from "./orders_screen";
import { PartnerDetail } from "./partner_detail";
import { PartnerList } from "./partner_list";
import { SettingsScreen } from "./settings_screen";

const SCREEN_TITLES = {
    home: "Preventa",
    activities: "Visitas",
    partners: "Clientes",
    catalog: "Catálogo",
    orders: "Pedidos",
    send: "Enviar",
    settings: "Configuración",
};

export class PreventaApp extends Component {
    static template = "sale_offline_app.App";
    static props = {};
    static components = {
        ActivitiesScreen,
        CatalogScreen,
        LockScreen,
        MainComponentsContainer,
        OrderBuilder,
        OrderDetail,
        OrdersScreen,
        PartnerDetail,
        PartnerList,
        SettingsScreen,
    };

    setup() {
        this.preventa = useService("preventa");
        this.notification = useService("notification");
        this.data = useState(this.preventa.state);
        this.state = useState({
            screen: "home",
            partnerId: null,
            activityId: false,
            // { order, fromHistory } of the order shown read-only.
            detail: null,
            tab: "order",
        });
    }

    get partner() {
        // Looked up on each render so a sync shows fresh partner data.
        return this.data.partners.find((partner) => partner.id === this.state.partnerId);
    }

    get detailOrder() {
        const detail = this.state.detail;
        // A local order is read again from the state: it may have been sent meanwhile.
        return detail && (detail.fromHistory ? detail.order : this.data.orders[detail.order.uuid]);
    }

    get tiles() {
        const today = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
        const pendingVisits = this.data.activities.filter(
            (activity) =>
                activity.date_deadline <= today &&
                !this.preventa.getActivityOrder(activity.id, this.data.orders)
        ).length;
        const drafts = this.preventa.getOrdersByState("draft", this.data.orders).length;
        return [
            { screen: "activities", icon: "fa-calendar-check-o", label: "Visitas", color: "#714B67", count: pendingVisits },
            { screen: "partners", icon: "fa-users", label: "Clientes", color: "#017E84" },
            { screen: "catalog", icon: "fa-th-list", label: "Catálogo", color: "#E46E78" },
            { screen: "orders", icon: "fa-history", label: "Pedidos", color: "#5B899E", count: drafts },
            { screen: "send", icon: "fa-cloud-upload", label: "Enviar", color: "#F4A261", count: this.readyCount },
            { screen: "settings", icon: "fa-cog", label: "Configuración", color: "#4C5767" },
        ];
    }

    get expiryWarning() {
        // Read through the reactive state so the banner follows a relink.
        if (!this.data.link) {
            return false;
        }
        const days = this.preventa.daysToExpiry();
        if (days === null || days > KEY_EXPIRY_WARNING_DAYS) {
            return false;
        }
        return days <= 0
            ? "La vinculación con Odoo venció."
            : `La vinculación con Odoo vence en ${days} día(s).`;
    }

    get readyCount() {
        return this.preventa.getOrdersByState("ready", this.data.orders).length;
    }

    get title() {
        if (this.partner) {
            return this.partner.ref ? `${this.partner.ref} - ${this.partner.name}` : this.partner.name;
        }
        if (this.detailOrder) {
            return this.detailOrder.partner_name;
        }
        return SCREEN_TITLES[this.state.screen];
    }

    get canGoBack() {
        return this.state.screen !== "home" || this.partner || this.state.detail;
    }

    goTo(screen) {
        Object.assign(this.state, { screen, partnerId: null, activityId: false, detail: null });
    }

    openPartner(partner, activityId = false) {
        Object.assign(this.state, { partnerId: partner.id, activityId, tab: "order", detail: null });
    }

    startActivity(activity) {
        Object.assign(this.state, { partnerId: activity.partner_id, activityId: activity.id, tab: "order" });
    }

    openOrder(order) {
        if (order.state === "draft") {
            // A draft is still being built: continue it in the order builder.
            Object.assign(this.state, {
                partnerId: order.partner_id,
                activityId: order.activity_id || false,
                tab: "order",
            });
        } else {
            this.state.detail = { order, fromHistory: false };
        }
    }

    openHistory(order) {
        this.state.detail = { order, fromHistory: true };
    }

    async repeatOrder(order) {
        const partner = this.data.partners.find((p) => p.id === order.partner_id);
        if (!partner) {
            this.notification.add("El cliente de ese pedido no está en el celular.", { type: "warning" });
            return;
        }
        const missing = await this.preventa.repeatOrder(partner, order.lines);
        if (missing.length) {
            this.notification.add(`No se copiaron (no están en el catálogo): ${missing.join(", ")}`, {
                type: "warning",
                sticky: true,
            });
        }
        this.openPartner(partner);
    }

    back() {
        if (this.partner) {
            // Back to the screen the customer was opened from.
            this.state.partnerId = null;
            this.state.activityId = false;
        } else if (this.state.detail) {
            this.state.detail = null;
        } else {
            this.goTo("home");
        }
    }

    logout() {
        const unsent = this.readyCount;
        if (unsent) {
            this.env.services.dialog.add(AlertDialog, {
                title: "Salir",
                body: `Tenés ${unsent} pedido(s) o no compra(s) sin enviar. Enviálos antes de salir.`,
            });
            return;
        }
        const drafts = this.preventa.getOrdersByState("draft", this.data.orders).length;
        const lost = drafts ? ` Se pierden ${drafts} pedido(s) en carga.` : "";
        this.env.services.dialog.add(ConfirmationDialog, {
            title: "Salir",
            body:
                "Se borran de este celular el acceso a Odoo y todos los datos: clientes, productos, visitas y pedidos." +
                `${lost} Después vas al ingreso de Odoo para que entre el próximo usuario.`,
            confirmLabel: "Salir",
            cancelLabel: "Cancelar",
            confirm: async () => {
                const revoked = await this.preventa.logout();
                this.goTo("home");
                if (!revoked) {
                    this.notification.add(
                        "Sin conexión: el acceso se borró del celular, pero la API key sigue vigente en Odoo hasta que la revoques desde tus preferencias.",
                        { type: "warning", sticky: true }
                    );
                }
            },
            cancel: () => {},
        });
    }
}
