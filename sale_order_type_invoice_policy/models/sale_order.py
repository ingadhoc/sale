##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_invoice_create_force(self):
        """
        Forzamos cantidades a facturar igual a cantidades pedidas (menos las
        ya facturadas)
        """
        self.ensure_one()
        for line in self.order_line:
            line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
        self.action_invoice_create(final=True)
        return self.action_view_invoice()
