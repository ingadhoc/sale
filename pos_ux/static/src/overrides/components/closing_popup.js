import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ClosePosPopup.prototype, {
    async handleClosingError(response) {
        if (response.pos_ux_unbilled) {
            this.dialog.add(AlertDialog, {
                title: _t("Cannot close session"),
                body: response.message,
                confirmLabel: _t("Review Orders"),
                confirm: () => {
                    this.props.close();
                    this.pos.navigate("TicketScreen", {
                        stateOverride: { filter: "SYNCED" },
                    });
                },
            });
            return;
        }
        return super.handleClosingError(response);
    },
});
