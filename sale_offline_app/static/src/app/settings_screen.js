import { Component, useState } from "@odoo/owl";
import { isDisplayStandalone } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";

/** Everything about syncing, linking and leaving the app. */
export class SettingsScreen extends Component {
    static template = "sale_offline_app.SettingsScreen";
    static props = { onLogout: Function };

    setup() {
        this.preventa = useService("preventa");
        this.data = useState(this.preventa.state);
        // Odoo's pwa service keeps the browser install prompt (beforeinstallprompt).
        this.pwa = useState(useService("pwa"));
        this.isInstalled = isDisplayStandalone();
    }

    get visitDays() {
        const days = [...new Set(this.data.activities.map((activity) => activity.date_deadline))].sort();
        return days.map((day) => day.split("-").reverse().join("/")).join(", ");
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

    onToggleAutoSend(ev) {
        this.preventa.setAutoSend(ev.target.checked);
    }
}
