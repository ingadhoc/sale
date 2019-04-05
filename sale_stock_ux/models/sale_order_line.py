##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
import odoo.addons.decimal_precision as dp


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # agregamos este campo para facilitar compatibilidad con
    # sale_usability_return_invoicing
    all_qty_delivered = fields.Float(
        string='All Delivered',
        compute='_compute_all_qty_delivered',
        help='Everything delivered without discounting the returns',
        digits=dp.get_precision('Product Unit of Measure'),
    )

    # TODO This should be computed field
    qty_returned = fields.Float(
        string='Returned',
        copy=False,
        default=0.0,
        digits=dp.get_precision('Product Unit of Measure'),
        readonly=True,
    )

    delivery_status = fields.Selection([
        ('no', 'Nothing to deliver'),
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

    @api.depends('qty_delivered', 'qty_returned')
    def _compute_all_qty_delivered(self):
        for rec in self:
            rec.all_qty_delivered = rec.qty_delivered + rec.qty_returned

    @api.depends(
        'order_id.state', 'qty_delivered', 'product_uom_qty',
        'order_id.force_delivery_status')
    def _compute_delivery_status(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for line in self:
            if line.state not in ('sale', 'done'):
                line.delivery_status = 'no'
                continue

            if line.order_id.force_delivery_status:
                line.order_id.delivery_status = \
                    line.order_id.force_delivery_status
                continue

            if float_compare(
                    line.all_qty_delivered, line.product_uom_qty,
                    # line.qty_delivered, line.product_uom_qty,
                    precision_digits=precision) == -1:
                delivery_status = 'to deliver'
            elif float_compare(
                    line.all_qty_delivered, line.product_uom_qty,
                    # line.qty_delivered, line.product_uom_qty,
                    precision_digits=precision) >= 0:
                delivery_status = 'delivered'
            else:
                delivery_status = 'no'
            line.delivery_status = delivery_status

    @api.multi
    def button_cancel_remaining(self):
        # la cancelación de kits no está bien resuelta ya que odoo solo computa
        # la cantidad entregada cuando todo el kit se entregó. Cuestión que,
        # por ahora, desactivamos la cancelación de kits
        bom_enable = 'bom_ids' in self.env['product.template']._fields

        for rec in self:
            if bom_enable:
                bom = self.env['mrp.bom']._bom_find(
                    product=rec.product_id)
                if bom.type == 'phantom':
                    raise UserError(_(
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
            rec.with_context(
                bypass_protecion=True).product_uom_qty = rec.qty_delivered
            to_cancel_moves = rec.move_ids.filtered(
                lambda x: x.state not in ['done', 'cancel'])
            to_cancel_moves._cancel_quantity()
            rec.order_id.message_post(
                body=_(
                    'Cancel remaining call for line "%s" (id %s), line '
                    'qty updated from %s to %s') % (
                        rec.name, rec.id,
                        old_product_uom_qty, rec.product_uom_qty))

    def _get_protected_fields(self):
        if self._context.get('bypass_protecion'):
            return []
        return super(SaleOrderLine, self)._get_protected_fields()

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        """
        Sobre escribimos este método para no permitir reducir cantidad
        we do it this way for this reason:
        https://github.com/odoo/odoo/commit/
        8fe7229e1984811f3456dbf502cb03fba879e180
        """
        if self._origin:
            product_uom_qty_origin = self._origin.read(
                ["product_uom_qty"])[0]["product_uom_qty"]
        else:
            product_uom_qty_origin = 0
        if (
                self.state == 'sale' and
                self.product_id.type in ['product', 'consu'] and
                self.product_uom_qty < product_uom_qty_origin):
            warning_mess = {
                'title': _('Ordered quantity decreased!'),
                'message': (
                    '¡Está reduciendo la cantidad pedida! Recomendamos usar'
                    ' el botón para cancelar remanente y'
                    ' luego setear la cantidad deseada.'),
            }
            self.product_uom_qty = self._origin.product_uom_qty
            return {'warning': warning_mess}
        return {}

    @api.multi
    def _get_delivered_qty(self):
        qty = super(SaleOrderLine, self)._get_delivered_qty()
        # parcheamos las devoluciones para los kits, lo hacemos analogo
        # a como hace odoo en la entrega, basicamente solo consideramos
        # devuelto si se devolvió todo (odoo considera entregado si se entrego
        # todo)
        bom_enable = 'bom_ids' in self.env['product.template']._fields
        if bom_enable:
            bom = self.env['mrp.bom']._bom_find(
                product=self.product_id)
            if bom.type == 'phantom':
                precision = self.env['decimal.precision'].precision_get(
                    'Product Unit of Measure')
                bom_returned = {}
                bom_returned[bom.id] = False
                product_uom_qty_bom = self.product_uom._compute_quantity(
                    self.product_uom_qty, bom.product_uom_id)
                bom_exploded = bom.explode(
                    self.product_id, product_uom_qty_bom)
                for bom_line in bom_exploded[1:][0]:
                    returned_qty = 0.0
                    for move in self.move_ids.filtered(
                            lambda r: (
                                r.product_id == bom_line[0].product_id and
                                r.state == 'done' and
                                not r.scrapped and
                                r.location_dest_id.usage != "customer" and
                                r.to_refund)):
                        returned_qty += move.product_uom._compute_quantity(
                            move.product_uom_qty,
                            bom_line[0].product_uom_id)
                    if float_compare(
                            returned_qty, bom_line[1].get('qty', 0.0),
                            precision_digits=precision) < 0:
                        bom_returned[bom.id] = False
                    else:
                        bom_returned[bom.id] = True
                if bom_returned and any(bom_returned.values()):
                    self.qty_returned = self.product_uom_qty
                    return 0.0
                elif bom_returned:
                    return qty

        # every time delivered qty is updated, we update qty returned
        self._get_qty_returned()
        return qty

    @api.multi
    def _get_qty_returned(self):
        """
        This method is called in the '_get_delivered_qty' method
        to update the 'qty returned' each time the 'qty
         delivered' is updated.
        """
        for rec in self:
            qty_returned = 0.0
            # we use same method as in sale_stock_picking_return_invoicing
            for move in rec.mapped('move_ids').filtered(
                lambda r: (r.state == 'done' and
                           not r.scrapped and
                           r.location_dest_id.usage != "customer" and
                           r.to_refund)):
                qty_returned += move.product_uom._compute_quantity(
                    move.product_uom_qty, rec.product_uom)
            rec.qty_returned = qty_returned

    @api.depends('qty_returned')
    def _get_to_invoice_qty(self):
        """
        Modificamos la funcion original para que si el producto es segun lo
        pedido, para que funcione el reembolo hacemos que la cantidad a
        facturar reste la cantidad devuelta.
        NOTA: solo lo hacemos si policy "order" porque en policy "delivered"
        odoo ya lo descuenta a la cantidad entregada y automáticamente lo
        termina facturando
        """
        super(SaleOrderLine, self)._get_to_invoice_qty()
        for line in self:
            # igual que por defecto, si no en estos estados, no hay a facturar
            if line.order_id.state not in ['sale', 'done']:
                continue
            if line.product_id.invoice_policy == 'order':
                line.qty_to_invoice = (
                    line.product_uom_qty - line.qty_returned -
                    line.qty_invoiced)

    @api.onchange('product_uom_qty', 'product_uom', 'route_id')
    def _onchange_product_id_check_availability(self):
        res = super(SaleOrderLine,
                    self)._onchange_product_id_check_availability()
        if self.order_id.warehouse_id.disable_sale_stock_warning and res.get(
                'warning', {}).get('title') == _('Not enough inventory!'):
            res.pop('warning')
        return res
