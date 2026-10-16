import { whenReady } from "@odoo/owl";
import { mountComponent } from "@web/env";
import { PreventaApp } from "./app";

whenReady(() => mountComponent(PreventaApp, document.body));
