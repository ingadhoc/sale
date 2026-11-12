import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("sale_ux_new_split_button_tour", {
    steps: () => [
        {
            // The core sale form uses the res_partner_many2one widget, which partner_autocomplete registers. A build
            // without that module logs "Missing widget" when the new quotation opens, and a tour fails on it. This is
            // done in a step, not at load: this file is also loaded in frontend pages, where "many2one" does not exist.
            content: "Make sure the partner widget of the sale form exists",
            trigger: ".o_sale_ux_new_split",
            run() {
                const fields = registry.category("fields");
                if (!fields.contains("res_partner_many2one")) {
                    fields.add("res_partner_many2one", fields.get("many2one"));
                }
            },
        },
        {
            content: "The caret opens the menu with the templates and creates nothing",
            trigger: ".o_sale_ux_new_split .o_sale_ux_new_toggle",
            run: "click",
        },
        {
            content: "The menu lists the quotation templates",
            trigger: ".o-dropdown--menu .dropdown-item:contains('Split button template')",
        },
        {
            content: "The text of the button creates a quotation right away",
            trigger: ".o_sale_ux_new_split > button:first-child",
            run: "click",
        },
        {
            content: "A new quotation is open, with no menu left over",
            trigger: ".o_form_view .o_form_editable:not(:has(.o-dropdown--menu)) [name=partner_id]",
        },
    ],
});
