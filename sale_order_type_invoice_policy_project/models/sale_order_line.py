##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _compute_qty_to_invoice(self):
        super()._compute_qty_to_invoice()
        for line in self.filtered(
            lambda sol: (
                sol.order_id.state == "sale"
                and sol.order_id.type_id.invoice_policy == "delivery"
                and sol.order_id.type_id.services_delivered
                and sol.product_id.type == "service"
                and sol.product_id.service_policy == "ordered_prepaid"
            )
        ):
            line.qty_to_invoice = line.product_uom_qty - line.quantity_returned - line.qty_invoiced
