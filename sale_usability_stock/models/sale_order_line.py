# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, fields, _
from openerp.exceptions import ValidationError
from openerp.tools.float_utils import float_compare
import openerp.addons.decimal_precision as dp


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # agregamoe este campo para facilitar compatibilidad con
    # sale_usability_return_invoicing
    all_qty_delivered = fields.Float(
        string='All Delivered',
        compute='_compute_all_qty_delivered',
        help='Todo lo entregado sin descontar las devoluciones',
        digits=dp.get_precision('Product Unit of Measure'),
    )

    @api.multi
    @api.depends('qty_delivered')
    def _compute_all_qty_delivered(self):
        for rec in self:
            rec.all_qty_delivered = rec.qty_delivered

    delivery_status = fields.Selection([
        ('no', 'Not purchased'),
        ('to deliver', 'To Deliver'),
        ('delivered', 'Delivered'),
    ],
        string='Delivery Status',
        compute='_compute_delivery_status',
        store=True,
        readonly=True,
        copy=False,
        default='no'
    )

    @api.depends(
        'order_id.state', 'qty_delivered', 'product_uom_qty',
        'order_id.manually_set_delivered')
    def _compute_delivery_status(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for line in self:
            if line.state not in ('sale', 'done'):
                line.delivery_status = 'no'
                continue

            if line.order_id.manually_set_delivered:
                line.order_id.delivery_status = 'delivered'
                continue

            if float_compare(
                    line.all_qty_delivered, line.product_uom_qty,
                    # line.qty_delivered, line.product_uom_qty,
                    precision_digits=precision) == -1:
                line.delivery_status = 'to deliver'
            elif float_compare(
                    line.all_qty_delivered, line.product_uom_qty,
                    # line.qty_delivered, line.product_uom_qty,
                    precision_digits=precision) >= 0:
                line.delivery_status = 'delivered'
            else:
                line.delivery_status = 'no'

    @api.multi
    def button_cancel_remaining(self):
        # la cancelación de kits no está bien resuelta ya que odoo solo computa
        # la cantidad entregada cuando todo el kit se entregó. Cuestión que,
        # por ahora, desactivamos la cancelación de kits
        bom_enable = 'bom_ids' in self.env['product.template']._fields

        for rec in self:
            if bom_enable:
                bom_id = self.env['mrp.bom']._bom_find(
                    product_id=rec.product_id.id,
                    properties=rec.property_ids.ids)
                bom = self.env['mrp.bom'].browse(bom_id)
                if bom.type == 'phantom':
                    raise ValidationError(_(
                        "Cancel remaining can't be called for Kit Products "
                        "(products with a bom of type kit)."))
            old_product_uom_qty = rec.product_uom_qty
            # Al final permitimos cancelar igual porque es necesario, por ej,
            # si no se va a entregar y ya está facturado y se quiere hacer
            # la nota de crédito. además se puede volver a subir la cantidad
            # si se requiere
            # if rec.qty_invoiced > rec.qty_delivered:
            #     raise ValidationError(_(
            #         'You can not cancel remianing qty to deliver because '
            #         'there are more product invoiced than the delivered. '
            #         'You should correct invoice or ask for a refund'))
            rec.product_uom_qty = rec.qty_delivered
            rec.procurement_ids.button_cancel_remaining()

            rec.order_id.message_post(
                body=_(
                    'Cancel remaining call for line "%s" (id %s), line '
                    'qty updated from %s to %s') % (
                        rec.name, rec.id,
                        old_product_uom_qty, rec.product_uom_qty))

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        """
        Sobre escribimos este método para no permitir reducir cantidad
        """
        if (
                self.state == 'sale' and
                self.product_id.type in ['product', 'consu'] and
                self.product_uom_qty < self._origin.product_uom_qty):
            warning_mess = {
                'title': _('Ordered quantity decreased!'),
                'message': (
                    '¡Está reduciendo la cantidad pedida! Esto no está '
                    'permitido, le recomendamos que entregue los productos '
                    'correspondientes y luego cancele el remanente utilzando '
                    'el botón para tal fin. Se restableció la cantidad a la '
                    'original'),
            }
            self.product_uom_qty = self._origin.product_uom_qty
            return {'warning': warning_mess}
        return {}
