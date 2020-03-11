##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _add_delivery_cost_to_so(self):
        """
        We set qty delivered 1 for every sale order line that:
        * is a delivery
        * dont has qty delivered
        * is a service
        * ordered qty is 1
        This way we guarantee we are changing delivery lines added with so
        button or automatically by the picking and that the user has not change
        for any reason
        """
        super()._add_delivery_cost_to_so()
        deliver_lines = self.sale_id.order_line.filtered(lambda x: (
            x.is_delivery and not x.qty_delivered and
            x.product_id.type == 'service' and x.product_uom_qty == 1.0))
        deliver_lines.update({'qty_delivered': 1.0})
