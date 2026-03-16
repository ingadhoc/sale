/** @odoo-module **/

import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

const userMenuRegistry = registry.category("user_menuitems");
const blockedItems = ["preferences", "portalAdhoc", "documentacionAdhoc", "chatwithus"];

function removeBlockedItems() {
    for (const key of blockedItems) {
        if (userMenuRegistry.contains(key)) {
            userMenuRegistry.remove(key);
        }
    }
}

user.hasGroup("portal_sale_distributor.group_portal_backend_distributor").then((isDistributor) => {
    if (!isDistributor) {
        return;
    }
    removeBlockedItems();
    userMenuRegistry.addEventListener("UPDATE", removeBlockedItems);
});
