import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const MAX_PIN_LENGTH = 6;

export class LockScreen extends Component {
    static template = "sale_offline_app.LockScreen";
    static props = {};

    setup() {
        this.preventa = useService("preventa");
        this.data = useState(this.preventa.state);
        this.state = useState({ typed: "", error: false });
        this.keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "⌫"];
    }

    get dots() {
        return Array.from({ length: this.data.pin.length }, (_, i) => i < this.state.typed.length);
    }

    press(key) {
        if (!key) {
            return;
        }
        this.state.error = false;
        if (key === "⌫") {
            this.state.typed = this.state.typed.slice(0, -1);
            return;
        }
        if (this.state.typed.length >= MAX_PIN_LENGTH) {
            return;
        }
        this.state.typed += key;
        if (this.state.typed.length === this.data.pin.length) {
            if (!this.preventa.unlock(this.state.typed)) {
                this.state.error = true;
                this.state.typed = "";
            }
        }
    }
}
