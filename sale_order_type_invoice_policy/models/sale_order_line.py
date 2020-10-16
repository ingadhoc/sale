##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # .invoice_policy (no hacemos depends en el .invoice_policy para que si
    # lo cambiamos mas adelante no reprosese todas las ventas)
    @api.depends('order_id.type_id')
    def _get_to_invoice_qty(self):
        """
        Modificamos la funcion original para sobre escribir con la policy
        del sale type si es que viene definida distinta de by product
        """
        super()._get_to_invoice_qty()
        for line in self.filtered(lambda sol: sol.order_id.state in [
            'sale', 'done'] and sol.order_id.type_id.invoice_policy !=
                'by_product'):
            type_policy = line.order_id.type_id.invoice_policy
            if type_policy in ['order', 'prepaid', 'prepaid_block_delivery']:
                line.qty_to_invoice = (
                    line.product_uom_qty - line.quantity_returned -
                    line.qty_invoiced)
            elif type_policy == 'delivery':
                line.qty_to_invoice = (
                    line.qty_delivered - line.qty_invoiced)
            else:
                raise UserError(_(
                    'Invoicing Policy %s not implemented!' % type_policy))
