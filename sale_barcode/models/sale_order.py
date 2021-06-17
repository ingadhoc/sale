##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, _


class SaleOrder(models.Model):

    _name = 'sale.order'
    _inherit = ['sale.order', 'barcodes.barcode_events_mixin']

    def on_barcode_scanned(self, barcode):
        product = self.env[
            'product.product'].search([('barcode', '=', barcode)])
        if product:
            self._add_product(product)
        else:
            return {'warning': {
                'title': _('Wrong barcode'),
                'message': _(
                    'The barcode "%(barcode)s" doesn\'t'
                    ' correspond to a proper product.') % {'barcode': barcode}
            }}

    def _add_product(self, product, qty=1.0):
        corresponding_line = self.order_line.filtered(
            lambda x: x.product_id == product)
        if corresponding_line:
            corresponding_line.product_uom_qty += qty
        else:
            line = self.order_line.new({
                'product_id': product.id,
                'product_uom_qty': qty,
                'order_id': self.id,
            })
            line.product_id_change()
            line.product_uom_change()
            line._onchange_discount()
        return True
