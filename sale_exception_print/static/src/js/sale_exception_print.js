import { registry } from "@web/core/registry";

const BASE_EXCEPTION_ERROR = "odoo.addons.base_exception.exceptions.BaseExceptionError";

async function popUpPrintException(env, action) {
    const controller = env.services.action.currentController;
    const resId = controller?.currentState?.resId || (action.params?.recordIds || [])[0];
    if (!resId) {
        return;
    }
    const popupAction = await env.services.orm.call(
        "sale.order",
        "action_popup_exceptions",
        [[resId]],
        { context: { print_exceptions: true } }
    );
    if (!popupAction) {
        return;
    }
    // Soft reload first, so the exceptions show up on the form view
    if (controller) {
        await env.services.action.restore(controller.jsId);
    }
    await env.services.action.doAction(popupAction, {
        onClose: () =>
            env.services.action.doAction({
                type: "ir.actions.client",
                tag: "soft_reload",
            }),
    });
}

function printExceptionErrorHandler(env, uncaughtError, originalError) {
    if (originalError.exceptionName !== BASE_EXCEPTION_ERROR) {
        return false;
    }
    let excData;
    try {
        excData = JSON.parse(originalError.data.message);
    } catch {
        return false;
    }
    if (!excData.print_exception) {
        return false;
    }
    env.services.action.doAction({
        type: "ir.actions.client",
        tag: "popup_print_exception",
        params: { recordIds: excData.record_ids || [] },
    });
    return true;
}

registry.category("actions").add("popup_print_exception", popUpPrintException);
// Before base_exception's handler (sequence 0), which pops up without the print context
registry
    .category("error_handlers")
    .add("sale_exception_print_error", printExceptionErrorHandler, { sequence: -1 });

registry.category("ir.actions.report handlers").add(
    "sale_exception_check",
    async (action, options, env) => {
        if (action.report_type === "qweb-pdf" && action.context?.active_model === "sale.order") {
            const activeIds = action.context.active_ids || [];
            if (activeIds.length > 0) {
                // Raises BaseExceptionError and stops the download when a rule blocks it
                await env.services.orm.call("sale.order", "detect_print_exceptions", [activeIds]);
            }
        }
        // No exceptions or not applicable, let other handlers process it
        return false;
    },
    { sequence: 0 }
);
