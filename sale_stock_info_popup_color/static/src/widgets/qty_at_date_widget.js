/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { QtyAtDateWidget } from "@sale_stock/widgets/qty_at_date_widget";

const { DateTime } = luxon;

patch(QtyAtDateWidget.prototype, {
    initCalcData() {
        super.initCalcData(...arguments);
        const { data } = this.props.record;
        // forecast_expected_date is the date of the incoming move covering the pending demand;
        // if it is already past, that receipt is overdue and the goods are not here.
        if (
            data.state === "sale" &&
            data.qty_to_deliver > 0 &&
            data.forecast_expected_date &&
            data.forecast_expected_date < DateTime.now().startOf("day")
        ) {
            this.calcData.forecasted_issue = true;
        }
    },
});
