/** @odoo-module **/

import { registry } from "@web/core/registry";

function icon(product, red) {
    const cls = red ? "a.text-danger" : "a:not(.text-danger)";
    return {
        content: `${product}: ${red ? "red" : "normal"} icon`,
        trigger: `.o_data_row:has(td:contains('${product}')) div.o_widget_qty_at_date_widget > ${cls}`,
    };
}

registry.category("web_tour.tours").add("sale_stock_info_popup_color_tour", {
    steps: () => [
        icon("Popup Color Overdue", true),
        icon("Popup Color On Time", false),
        icon("Popup Color Late", true),
        icon("Popup Color Received", false),
        icon("Popup Color Partial", true),
    ],
});
