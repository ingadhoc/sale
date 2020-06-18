##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    all_qty_delivered = fields.Float(
        string='All Delivered',
        compute='_compute_all_qty_delivered',
        help='Everything delivered without discounting the returns',
        digits='Product Unit of Measure',
    )

    qty_returned = fields.Float(
        string='Returned',
        compute='_compute_qty_returned',
        copy=False,
        digits='Product Unit of Measure',
    )

    delivery_status = fields.Selection([
        ('no', 'Nothing to deliver'),
        ('to deliver', 'To Deliver'),
        ('delivered', 'Delivered'),
    ],
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
                line.delivery_status = line.order_id.force_delivery_status
                continue

            if float_compare(
                    line.all_qty_delivered, line.product_uom_qty,
                    precision_digits=precision) == -1:
                delivery_status = 'to deliver'
            elif float_compare(
                    line.all_qty_delivered, line.product_uom_qty,
                    precision_digits=precision) >= 0:
                delivery_status = 'delivered'
            else:
                delivery_status = 'no'
            line.delivery_status = delivery_status

    def button_cancel_remaining(self):
        # la cancelación de kits no está bien resuelta ya que odoo solo computa
        # la cantidad entregada cuando todo el kit se entregó. Cuestión que,
        # por ahora, desactivamos la cancelación de kits
        bom_enable = 'bom_ids' in self.env['product.template']._fields

        for rec in self.filtered('product_id'):
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
        return super()._get_protected_fields()

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

    @api.depends('qty_delivered_method', 'move_ids.state', 'move_ids.scrapped',
                 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_returned(self):
        for order_line in self:
            qty_returned = 0.0
            # we use same method as in odoo use to delivery's
            if order_line.qty_delivered_method == 'stock_move':
                return_moves = order_line.mapped('move_ids').filtered(
                    lambda r: (r.state == 'done' and
                               not r.scrapped and
                               r.location_dest_id.usage != "customer" and
                               r.to_refund))
                for move in return_moves:
                    qty_returned += move.product_uom._compute_quantity(
                        move.product_uom_qty, order_line.product_uom)
                bom_enable = 'bom_ids' in self.env['product.template']._fields
                if bom_enable:
                    boms = return_moves.mapped('bom_line_id.bom_id')
                    dropship = False
                    if not boms and any([m._is_dropshipped()
                                         for m in return_moves]):
                        boms = boms._bom_find(
                            product=order_line.product_id,
                            company_id=order_line.company_id.id,
                            bom_type='phantom')
                        dropship = True
                    # We fetch the BoMs of type kits linked to the order_line,
                    # the we keep only the one related to the finished produst.
                    # This bom shoud be the only one since bom_line_id was written on the moves
                    relevant_bom = boms.filtered(
                        lambda b: b.type == 'phantom' and (b.product_id == order_line.product_id or (
                            b.product_tmpl_id == order_line.product_id.product_tmpl_id and not b.product_id)))
                    if relevant_bom:
                        # In case of dropship, we use a 'all or nothing' policy since 'bom_line_id' was
                        # not written on a move coming from a PO.
                        # FIXME: if the components of a kit have different suppliers, multiple PO
                        # are generated. If one PO is confirmed and all the others are in draft, receiving
                        # the products for this PO will set the qty_delivered. We might need to check the
                        # state of all PO as well... but sale_mrp doesn't depend on purchase.
                        if dropship:
                            if order_line.move_ids and all(
                                    [m.state == 'done' for m in return_moves]):
                                qty_returned = order_line.product_uom_qty
                            else:
                                qty_returned = 0.0
                            continue
                        filters = {'outgoing_moves': lambda m: m.location_dest_id.usage == 'customer' and (
                            not m.origin_returned_move_id or (
                                m.origin_returned_move_id and m.to_refund)),
                            'incoming_moves': lambda m: m.location_dest_id.usage != 'customer' and m.to_refund}
                        order_qty = order_line.product_uom._compute_quantity(
                            order_line.product_uom_qty, relevant_bom.product_uom_id)
                        qty_returned = return_moves._compute_kit_quantities(
                            order_line.product_id, order_qty, relevant_bom, filters)

                    # If no relevant BOM is found, fall back on the all-or-nothing policy. This happens
                    # when the product sold is made only of kits. In this case, the BOM of the stock moves
                    # do not correspond to the product sold => no relevant BOM.
                    elif boms:
                        if all([m.state == 'done' for m in return_moves]):
                            qty_returned = order_line.product_uom_qty
                        else:
                            qty_returned = 0.0
            order_line.qty_returned = qty_returned

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
        super()._get_to_invoice_qty()
        for line in self:
            # igual que por defecto, si no en estos estados, no hay a facturar
            if line.order_id.state not in ['sale', 'done']:
                continue
            if line.product_id.invoice_policy == 'order':
                line.qty_to_invoice = (
                    line.product_uom_qty - line.qty_returned -
                    line.qty_invoiced)
