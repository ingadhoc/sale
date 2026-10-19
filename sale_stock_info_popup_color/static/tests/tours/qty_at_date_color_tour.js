import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("sale_stock_info_popup_color_tour", {
    steps: () => [
        {
            content: "Incoming product without free stock today: red icon",
            trigger: ".o_data_row:has(td:contains('Popup Color Incoming')) div.o_widget_qty_at_date_widget > a.text-danger",
        },
        {
            content: "Product with free stock today: normal icon",
            trigger: ".o_data_row:has(td:contains('Popup Color On Hand')) div.o_widget_qty_at_date_widget > a:not(.text-danger)",
        },
    ],
});
