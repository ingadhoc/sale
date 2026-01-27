/** @odoo-module **/

import { StaticList } from "@web/model/relational_model/static_list";
import { Record } from "@web/model/relational_model/record";
import { patch } from "@web/core/utils/patch";

const pagerStates = new Map();

patch(Record.prototype, {
    _createStaticListDatapoint(data, fieldName, params) {
        const list = super._createStaticListDatapoint(data, fieldName, params);
        if (this.resModel === 'sale.order') {
            list._x2manyKey = `${this.resModel}:${fieldName}`;
            const state = pagerStates.get(list._x2manyKey);
            if (state) {
                const currentCount = data[fieldName]?.currentIds?.length || list.count;
                const useLimit = state.showAll ? currentCount : state.limit;
                if (state.offset !== list.config.offset || useLimit !== list.config.limit) {
                    list._load({ offset: state.offset, limit: useLimit });
                }
            }
        }
        return list;
    }
});

patch(StaticList.prototype, {
    load(params = {}) {
        if (this._x2manyKey && params.limit !== undefined && params.offset !== undefined) {
            pagerStates.set(this._x2manyKey, {
                offset: params.offset,
                limit: params.limit,
                showAll: params.limit === this.count
            });
        }
        return super.load(params);
    }
});
