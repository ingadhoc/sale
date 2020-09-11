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
        'product_id',
        'product_uom_qty',
        'product_uom')
    def _compute_virtual_available(self):
        for rec in self.filtered(
                lambda sol: sol.order_id.state in ['draft', 'sent']):
            product_uom = rec.product_id.uom_id
            virtual_available = rec.product_id.with_context(warehouse=rec.order_id.warehouse_id.id).virtual_available
            if product_uom != rec.product_uom:
                virtual_available = product_uom._compute_quantity(virtual_available, rec.product_uom)
            rec.virtual_available = virtual_available - rec.product_uom_qty
