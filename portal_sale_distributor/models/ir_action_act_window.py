##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api
from odoo.tools.safe_eval import safe_eval


class ActWindowView(models.Model):
    _inherit = 'ir.actions.act_window'

    def read(self, fields=None, load='_classic_read'):
        result = super().read(fields, load=load)
        if result and result[0].get('context'):
            ctx = safe_eval(result[0].get('context', '{}'))
            if ctx.get('portal_products'):
                pricelist = self.env.user.partner_id.property_product_pricelist
                ctx.update({'pricelist': pricelist.id, 'partner': self.env.user.partner_id})
                result[0].update({'context': ctx})
        return result
