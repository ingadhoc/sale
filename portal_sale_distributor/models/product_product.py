##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api
from odoo.tools import pycompat


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _compute_product_price(self):
        # other approach could be to inherit the method that builds the
        # action (like fields view get)
        super(ProductProduct, self)._compute_product_price()
        if self._context.get('portal_products'):
            pricelist = self.env.user.partner_id.property_product_pricelist.id
            context = dict(self._context, pricelist=pricelist,
                           partner=self.env.user.partner_id)
            self2 = self.with_context(
                context) if self._context != context else self
            for rec, rec2 in pycompat.izip(self, self2):
                rec.price = rec2.price
