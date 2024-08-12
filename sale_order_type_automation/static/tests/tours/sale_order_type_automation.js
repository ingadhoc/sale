/** @odoo-module **/

import tour from "web_tour.tour";


tour.register("sale_order_type_automation_tour", {
    url: "/web",
    test: true
}, [
    tour.stepUtils.showAppsMenuItem(),
    {
        content: "Open Sales app.",
        trigger: ".o_menuitem[data-menu-xmlid='sale.sale_menu_root']",
    },
    {
        content: "Selecting button to add a sales order.",
        trigger: "button.btn-primary.o_list_button_add",
        run: "click",
    },
    {
        content: "Writing partner name.",
        trigger: ".o_input[id='partner_id']",
        run: "text Deco Addict"
    },
    {
        content: "Selecting partner.",
        trigger: "a:contains('Deco Addict')",
        run: "click"
    },
    {
        content: "Click here to add some products or services to your quotation.",
        trigger: ".o_field_x2many_list_row_add > a",
    },
    {
        content: "Writing product name.",
        trigger: "div[name='product_template_id'] input",
        run: "text Test Product"
    },
    {
        content: "Selecting product.",
        trigger: "a:contains('Test Product')",
        run: "click"
    },
    {
        content: "Writing type of sales order.",
        trigger: ".o_input[id='type_id']",
        extra_trigger: "div:contains('IVA 21%')",
        run: "text Picking And Invoice Automation (Validate)"
    },
    {
        content: "Selecting type of sales order.",
        trigger: "a:contains('Picking And Invoice Automation (Validate)')",
        run: "click"
    },
    ...tour.stepUtils.saveForm(),
    {
        content: "Confirm sales order.",
        trigger: "button[name='action_confirm']",
        run: "click",
    },
]);
