# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import api, models, _
from openerp.exceptions import ValidationError


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
        super(SaleOrderLine, self)._get_to_invoice_qty()
        for line in self:
            # igual que por defecto, si no en estos estados, no hay a facturar
            if line.order_id.state not in ['sale', 'done']:
                continue

            type_policy = line.order_id.type_id.invoice_policy
            # if by product, dont overwrite invoice qty
            # si no hay type_policy puede ser por ordenes que antes de instalar
            # sale_order_type que no tienen type
            if not type_policy or type_policy == 'by_product':
                continue
            # elif type_policy == 'delivery':
            # if order, we force ordered qty
            # por ahora las dos opciones que quedan son prepaid y order
            # y ambas funcionan como order una vez configramada
            elif type_policy in ['order', 'prepaid']:
                line.qty_to_invoice = (
                    line.product_uom_qty - line.qty_returned -
                    line.qty_invoiced)
            else:
                raise ValidationError(_(
                    'Invoicing Policy %s not implemented!' % type_policy))
