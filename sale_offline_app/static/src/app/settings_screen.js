import { Component, useState } from "@odoo/owl";
import { isDisplayStandalone } from "@web/core/browser/feature_detection";
import { humanSize } from "@web/core/utils/binary";
import { useService } from "@web/core/utils/hooks";
import { formatDate } from "./utils";

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
        this.formatDate = formatDate;
    }

    get visitDays() {
        const days = [...new Set(this.data.activities.map((activity) => activity.date_deadline))].sort();
        return days.map((day) => day.split("-").reverse().join("/")).join(", ");
    }

    formatBytes(bytes) {
        return !bytes && bytes !== 0 ? "?" : humanSize(bytes);
    }

    onToggleAutoSend(ev) {
        this.preventa.setAutoSend(ev.target.checked);
    }
}
