import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("sale_ux_order_line_pager_top_tour", {
    steps: () => [
        {
            // The core sale form uses the res_partner_many2one widget, which partner_autocomplete registers. A build
            // without that module logs "Missing widget" when the order opens, and a tour fails on it. This is done
            // in a step, not at load: this file is also loaded in frontend pages, where "many2one" does not exist.
            content: "Make sure the partner widget of the sale form exists",
            trigger: ".o_sale_order_line_o2m",
            run() {
                const fields = registry.category("fields");
                if (!fields.contains("res_partner_many2one")) {
                    fields.add("res_partner_many2one", fields.get("many2one"));
                }
            },
        },
        {
            content: "The pager above the lines shows the first page",
            trigger: ".o_sale_ux_pager_top .o_pager_value:contains('1-40')",
        },
        {
            content: "The pager below the lines is still there, on the same page",
            trigger: ".o_x2m_control_panel .o_pager_value:contains('1-40')",
        },
        {
            content: "Go to the next page with the pager above",
            trigger: ".o_sale_ux_pager_top .o_pager_next",
            run: "click",
        },
        {
            content: "Both pagers moved to the second page",
            trigger: ".o_sale_ux_pager_top .o_pager_value:contains('41-')",
        },
        {
            content: "The one below moved too",
            trigger: ".o_x2m_control_panel .o_pager_value:contains('41-')",
        },
    ],
});
