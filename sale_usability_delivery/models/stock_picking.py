##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
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
        super(StockPicking, self)._add_delivery_cost_to_so()
        deliver_lines = self.sale_id.order_line.filtered(lambda x: (
            x.is_delivery and not x.qty_delivered and
            x.product_id.type == 'service' and x.product_uom_qty == 1.0))
        deliver_lines.write({'qty_delivered': 1.0})

        # TODO, borrar, volvimos a esta version
        # Now we overwrite method to make it more robust, we basically do the
        # same as odoo method but we keep info of which line was created.
        # Then, if carrier price is:
        # * zero: we add with qty 0 so nothing is needed to be invoiced or sent
        # * not zero: we keep qty so it is set to be invoiced but we set it
        # as delivered so you dont need to set it manually

        # sale_order = self.sale_id
        # if sale_order.invoice_shipping_on_delivery:
        #     sol = sale_order._create_delivery_line(
        #         self.carrier_id, self.carrier_price)
        #     if not self.carrier_price:
        #         sol.product_uom_qty = 0.0
        #     else:
        #         sol.write({'qty_delivered': 1.0})
