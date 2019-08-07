odoo.define('sale_barcode.SaleBarcodeHandler', function (require) {
"use strict";

var core = require('web.core');
var AbstractField = require('web.AbstractField');
var field_registry = require('web.field_registry');

var _t = core._t;


var SaleBarcodeHandler = AbstractField.extend({
    init: function() {
        this._super.apply(this, arguments);

        this.trigger_up('activeBarcode', {
            name: this.name,
            fieldName: 'order_line',
            notifyChange: true,
            quantity: 'product_uom_qty',
            setQuantityWithKeypress: true,
            commands: {
                barcode: '_barcodeAddX2MQuantity',
            }
        });
    },
});

field_registry.add('sale_barcode_handler', SaleBarcodeHandler);

return SaleBarcodeHandler;

});
