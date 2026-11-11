import { registry } from "@web/core/registry";
import {
    SaleOrderLineOne2Many,
    saleOrderLineOne2Many,
} from "@sale/js/sale_order_line_field/sale_order_line_field";

/**
 * The core sends the x2many control panel (create buttons and pager) below the lines with css. We also show
 * the pager above them, as in previous versions: both move the same page.
 */
export class SaleUxOrderLineOne2Many extends SaleOrderLineOne2Many {
    static template = "sale_ux.SaleOrderLineOne2Many";
}

registry.category("fields").add(
    "sol_o2m",
    { ...saleOrderLineOne2Many, component: SaleUxOrderLineOne2Many },
    { force: true }
);
