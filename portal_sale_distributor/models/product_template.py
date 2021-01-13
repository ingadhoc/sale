##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _compute_template_price(self):
        # other approach could be to inherit the method that builds the
        # action (like fields view get)
        super()._compute_template_price()
        if self._context.get('portal_products'):
            pricelist = self.env.user.partner_id.property_product_pricelist
            context = dict(self._context, pricelist=pricelist.id,
                           partner=self.env.user.partner_id)
            self2 = self.with_context(context) if self._context != context else self
            for rec, rec2 in zip(self, self2):
                rec.price = rec2.price
