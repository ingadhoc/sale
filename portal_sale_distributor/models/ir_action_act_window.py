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
        for value in result:
            if value.get('context') and 'portal_products' in value.get('context'):
                eval_ctx = dict(self.env.context)
                try:
                    ctx = safe_eval(value.get('context', '{}'), eval_ctx)
                except:
                    ctx = {}
                pricelist = self.env.user.partner_id.property_product_pricelist
                ctx.update({'pricelist': pricelist.id, 'partner': self.env.user.partner_id.id})
                value.update({'context': str(ctx)})
        return result
