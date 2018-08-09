##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    virtual_available = fields.Float(
        compute="_compute_virtual_available",
        string='Saldo Stock',
    )

    @api.depends(
        'product_uom_qty',
        'product_id')
    def _compute_virtual_available(self):
        for rec in self.filtered(lambda sol: sol.order_id.state == 'draft'):
            rec.virtual_available = rec.product_id.with_context(
                warehouse=rec.order_id.warehouse_id.id
            ).virtual_available - rec.product_uom_qty

    @api.onchange('product_uom_qty', 'product_uom', 'route_id')
    def _onchange_product_id_check_availability(self):
        res = super(SaleOrderLine,
                    self)._onchange_product_id_check_availability()
        if self.order_id.warehouse_id.disable_sale_stock_warning or False:
            res.update({'warning': {}})
        return res
