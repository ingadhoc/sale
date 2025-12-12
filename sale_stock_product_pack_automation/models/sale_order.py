##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def run_invoicing_atomation(self):
        lines = self.mapped("order_line").filtered(
            lambda x: x.pack_child_line_ids
            and x.product_id.pack_ok
            and x.qty_delivered_method == "stock_move"
            and x.product_uom_qty
        )
        if lines:
            lines._compute_quantity_returned()
        super().run_invoicing_atomation()
