# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, api


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.one
    @api.depends(
        'product_uom_qty',
        'product_id')
    def _fnct_line_stock(self):
        available = False
        if self.order_id.state == 'draft':
            available = self.product_id.with_context(
                warehouse=self.order_id.warehouse_id.id
            ).virtual_available - self.product_uom_qty
        self.virtual_available = available
        if available >= 0.0:
            available = True
        else:
            available = False
        self.virtual_available_boolean = available

    virtual_available = fields.Float(
        compute="_fnct_line_stock", string='Saldo Stock')
    virtual_available_boolean = fields.Boolean(
        compute="_fnct_line_stock", string='Saldo Stock')

    @api.onchange('product_uom_qty', 'product_uom', 'route_id')
    def _onchange_product_id_check_availability(self):
        res = super(SaleOrderLine,
                    self)._onchange_product_id_check_availability()
        if self.order_id.warehouse_id.disable_sale_stock_warning or False:
            res.update({'warning': {}})
        return res
