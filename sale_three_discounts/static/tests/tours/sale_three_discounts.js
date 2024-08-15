/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("sale_three_discounts_tour", {
    url: "/web",
    test: true,
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: ".o_app[data-menu-xmlid='sale.sale_menu_root']",
        },
        {
            trigger: "button.btn-primary.o_list_button_add",
            run: "click",
        },
        {
            trigger: "div[name='partner_id'] input",
            run: "text Deco Addict"
        },
        {
            trigger: "a:contains('Deco Addict')",
            run: "click"
        },
        {
            trigger: ".o_field_x2many_list_row_add > a",
        },
        {
            trigger: "div[name='product_template_id'] input",
            run: "text Test Product 1"
        },
        {
            trigger: "a:contains('Test Product 1')",
            run: "click"
        },
        {
            trigger: "div[name='discount1'] input",
            run: "text 10"
        },
        {
            trigger: "div[name='discount2'] input",
            extra_trigger: "div[name='discount']:contains('10.00')",
            run: "text 10"
        },
        {
            trigger: "div[name='discount3'] input",
            extra_trigger: "div[name='discount']:contains('19.00')",
            run: "text 10"
        },
        {
            trigger: "div[name='pricelist_id'] input",
            extra_trigger: "div[name='discount']:contains('27.10')",
            run: "text Pricelist with discount"
        },
        {
            trigger: "a:contains('Pricelist with discount (ARS)')",
            run: "click"
        },
        {
            trigger: "div[name='pricelist_id'] input",
            extra_trigger: "div[name='price_subtotal']:contains('61.97')",
            run: "text Pricelist without discount"
        },
        {
            trigger: "a:contains('Pricelist without discount (ARS)')",
            run: "click"
        },
        {
            trigger: "div[name='discount']:contains('15.00')",
            extra_trigger: "div[name='price_subtotal']:contains('85.00')",
            run: () => {}
        },
        ...stepUtils.saveForm()
]});
