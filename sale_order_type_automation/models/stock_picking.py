##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        """
        On picking confirmation we check if invoice should be created
        """
        res = super()._action_done()
        pickings = self.filtered(lambda p: p.location_id._is_outgoing() or p.location_dest_id._is_outgoing())
        sale_orders = pickings.sudo().mapped("sale_id")
        # The invoice is created, posted and rendered right below, so anything it
        # has to show is settled first, and only on the pickings being invoiced.
        orders_to_invoice = sale_orders._orders_to_invoice_automatically()
        pickings.filtered(lambda p: p.sudo().sale_id in orders_to_invoice)._prepare_for_automatic_invoicing()
        sale_orders.run_invoicing_atomation()
        return res
