# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('order_id.type_id.invoice_policy')
    def _get_to_invoice_qty(self):
        """
        Modificamos la funcion original para sobre escribir con la policy
        del sale type si es que viene definida distinta de by product
        """
        super(SaleOrderLine, self)._get_to_invoice_qty()
        for line in self:
            type_policy = line.order_id.type_id.invoice_policy
            if type_policy == 'by_product' or line.order_id.state not in [
                    'sale', 'done']:
                continue
            # por ahora las dos opciones que quedan son prepaid y order
            # y ambas funcionan como order una vez configramada
            line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
