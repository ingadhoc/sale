import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ProjectTaskFormController } from "@project/views/project_task_form/project_task_form_controller";

patch(ProjectTaskFormController.prototype, {
    async onWillSaveRecord(record, changes) {
        if (record.resId && "sale_line_id" in record._changes) {
            const count = await record.model.orm.call(record.resModel, "count_timesheets_to_relink", [[record.resId]]);
            if (count) {
                const confirmed = await new Promise((resolve) => {
                    this.env.services.dialog.add(ConfirmationDialog, {
                        title: _t("Confirmation"),
                        body: _t(
                            "Changing the sales order item of this task will recalculate the sales order item of its timesheet entries that were not chosen by hand, validated or invoiced (total: %s). Are you sure you want to continue?",
                            count
                        ),
                        confirm: () => resolve(true),
                        cancel: () => resolve(false),
                    });
                });
                if (!confirmed) {
                    // not awaited: the save in progress holds the mutex of the model
                    record.discard();
                    return false;
                }
            }
        }
        return super.onWillSaveRecord(...arguments);
    },
});
