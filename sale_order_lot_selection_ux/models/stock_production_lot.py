##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class ProductionLot(models.Model):
    _inherit = 'stock.lot'

    def _compute_display_name(self):
        if not self._context.get('from_sale_line', False) or not self._context.get('warehouse_id', False) :
            return super()._compute_display_name()
        location = self.env['stock.warehouse'].browse(self._context.get('warehouse_id', [])).lot_stock_id
        for rec in self:
            quants = rec.quant_ids.filtered(lambda x :  x.location_id == location or x.location_id.location_id == location)
            qty = quants and sum(quants.mapped(lambda x: x.quantity - x.reserved_quantity)) or 0.0
            name = rec.name + " (%s %s) " % (qty, quants and quants[0].product_uom_id.name or ' ')
            rec.display_name = name
