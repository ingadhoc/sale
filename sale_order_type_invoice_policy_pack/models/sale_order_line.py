##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _compute_qty_to_invoice(self):
        super()._compute_qty_to_invoice()
        main_pack_lines = self.filtered("pack_parent_line_id").mapped("pack_parent_line_id")
        for line in main_pack_lines.filtered(
            lambda sol: sol.order_id.state == "sale" and sol.order_id.type_id.invoice_policy == "delivery"
        ):
            # Verificar si todos los componentes del pack están completamente entregados
            all_delivered = all(child.qty_delivered >= child.product_uom_qty for child in line.pack_child_line_ids)
            if all_delivered:
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
            else:
                line.qty_to_invoice = 0.0
