odoo.define('sale_barcode.SaleBarcodeHandler', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var fieldRegistry = require('web.field_registry');


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


fieldRegistry.add('sale_barcode_handler', SaleBarcodeHandler);

return SaleBarcodeHandler;

});
