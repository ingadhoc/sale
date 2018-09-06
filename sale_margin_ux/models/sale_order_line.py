##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _compute_margin(self, order_id, product_id, product_uom_id):
        """ Overwrite this method and use frm_cur from product currency instead
        of user company currency
        This should be fixed on odoo
        """
        frm_cur = product_id.currency_id
        to_cur = order_id.pricelist_id.currency_id
        purchase_price = product_id.standard_price
        if product_uom_id != product_id.uom_id:
            purchase_price = self.env['product.uom']._compute_price(
                product_id.uom_id.id, purchase_price,
                to_uom_id=product_uom_id.id)
        ctx = self.env.context.copy()
        ctx['date'] = order_id.date_order
        price = frm_cur.with_context(ctx).compute(
            purchase_price, to_cur, round=False)
        return price
