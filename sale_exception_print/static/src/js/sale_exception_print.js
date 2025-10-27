/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("ir.actions.report handlers").add("sale_exception_check", async (action, options, env) => {
    if (action.report_type === 'qweb-pdf' && action.context && action.context.active_model === 'sale.order') {
        const activeIds = action.context.active_ids || [];
        if (activeIds.length > 0) {
            const result = await env.services.orm.call(
                'sale.order',
                'check_print_exceptions_for_action',
                [activeIds]
            );

            if (result && result.has_exceptions) {
                // Reload the form first to show the exceptions
                await env.services.action.doAction("soft_reload");
                // Show the exception wizard instead of printing
                await env.services.action.doAction(result.action);
                // Return true to indicate we handled the action and stop further processing
                return true;
            }
        }
    }

    // No exceptions or not applicable, let other handlers process it
    return false;
}, { sequence: 0 }); // High priority to run first
