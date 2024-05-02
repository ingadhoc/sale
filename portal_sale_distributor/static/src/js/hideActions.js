/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { onWillStart } from "@odoo/owl";

patch(ListController.prototype, "hideActionsPatch", {
    setup() {
        this._super(...arguments);
        onWillStart(async () => {
            this.isUserInDistributorGroup = await this.userService.hasGroup("portal_sale_distributor.group_portal_backend_distributor");
        });
    },
    getActionMenuItems() {
        const actionMenuItems = this._super(...arguments);
        if (this.isUserInDistributorGroup) {
            actionMenuItems.other = [];
        }
        return actionMenuItems;
    },
});
