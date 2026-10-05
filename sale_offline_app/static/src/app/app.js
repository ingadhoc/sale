import { Component, useState } from "@odoo/owl";
import { isDisplayStandalone } from "@web/core/browser/feature_detection";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useService } from "@web/core/utils/hooks";
import { ActivitiesScreen } from "./activities_screen";
import { LockScreen } from "./lock_screen";
import { OrderBuilder } from "./order_builder";
import { KEY_EXPIRY_WARNING_DAYS } from "./preventa_service";
import { OrderDetail } from "./order_detail";
import { OrdersScreen } from "./orders_screen";
import { PartnerDetail } from "./partner_detail";
import { PartnerList } from "./partner_list";

export class PreventaApp extends Component {
    static template = "sale_offline_app.App";
    static props = {};
    static components = {
        ActivitiesScreen,
        LockScreen,
        MainComponentsContainer,
        OrderBuilder,
        OrderDetail,
        OrdersScreen,
        PartnerDetail,
        PartnerList,
    };

    setup() {
        this.preventa = useService("preventa");
        this.data = useState(this.preventa.state);
        // Odoo's pwa service keeps the browser install prompt (beforeinstallprompt).
        this.pwa = useState(useService("pwa"));
        this.isInstalled = isDisplayStandalone();
        this.state = useState({
            screen: "activities",
            partnerId: null,
            activityId: false,
            orderUuid: null,
            tab: "order",
            showStatus: false,
        });
    }

    get partner() {
        // Looked up on each render so a sync shows fresh partner data.
        return this.data.partners.find((partner) => partner.id === this.state.partnerId);
    }

    openPartner(partner) {
        this.state.partnerId = partner.id;
        this.state.activityId = false;
        this.state.tab = "order";
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
            return this.partner.name;
        }
        if (this.state.screen === "orders") {
            return this.state.orderUuid ? this.data.orders[this.state.orderUuid]?.partner_name : "Pedidos";
        }
        return this.state.screen === "partners" ? "Clientes" : "Visitas";
    }

    goTo(screen) {
        Object.assign(this.state, { screen, partnerId: null, activityId: false, orderUuid: null });
    }

    startActivity(activity) {
        Object.assign(this.state, { partnerId: activity.partner_id, activityId: activity.id, tab: "order" });
    }

    openOrder(order) {
        if (order.state === "draft") {
            // A draft is still being built: continue it in the order builder.
            this.state.screen = "partners";
            this.state.partnerId = order.partner_id;
            this.state.activityId = order.activity_id || false;
            this.state.tab = "order";
        } else {
            this.state.orderUuid = order.uuid;
        }
    }

    back() {
        if (this.partner) {
            // Back to the list the customer was opened from.
            this.state.partnerId = null;
            this.state.activityId = false;
        } else if (this.state.orderUuid) {
            this.state.orderUuid = null;
        }
    }

    installApp() {
        this.pwa.show();
    }

    logout() {
        const unsent = this.readyCount;
        if (unsent) {
            this.env.services.dialog.add(AlertDialog, {
                title: "Salir",
                body: `Tenés ${unsent} pedido(s) cerrado(s) sin enviar. Enviálos antes de salir.`,
            });
            return;
        }
        const drafts = this.preventa.getOrdersByState("draft", this.data.orders).length;
        const lost = drafts ? ` Se pierden ${drafts} pedido(s) en carga.` : "";
        this.env.services.dialog.add(ConfirmationDialog, {
            title: "Salir",
            body:
                "Se borran de este celular el acceso a Odoo y todos los datos: clientes, productos, visitas y pedidos." +
                `${lost} Para volver a usar la app hay que vincularlo de nuevo y sincronizar.`,
            confirmLabel: "Salir",
            cancelLabel: "Cancelar",
            confirm: async () => {
                const revoked = await this.preventa.logout();
                this.state.showStatus = false;
                this.state.screen = "partners";
                this.state.partnerId = null;
                this.state.orderUuid = null;
                if (!revoked) {
                    this.env.services.notification.add(
                        "Sin conexión: el acceso se borró del celular, pero la API key sigue vigente en Odoo hasta que la revoques desde tus preferencias.",
                        { type: "warning", sticky: true }
                    );
                }
            },
            cancel: () => {},
        });
    }

    formatDate(iso) {
        return iso ? new Date(iso).toLocaleString("es-AR", { hourCycle: "h23" }) : "";
    }

    formatBytes(bytes) {
        if (!bytes && bytes !== 0) {
            return "?";
        }
        const units = ["B", "KB", "MB", "GB", "TB"];
        let value = bytes;
        let unit = 0;
        while (value >= 1024 && unit < units.length - 1) {
            value /= 1024;
            unit++;
        }
        return `${value.toFixed(1)} ${units[unit]}`;
    }
}
