# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import api, models


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    @api.cr_uid_ids_context
    def transfer_details(self, cr, uid, picking, context=None):
        if not context:
            context = {}
        else:
            context = context.copy()
        context.update({
            'active_model': self._name,
            'active_ids': picking,
            'active_id': len(picking) and picking[0] or False
        })

        created_id = self.pool['stock.transfer_details'].create(
            cr, uid, {'picking_id': len(picking) and picking[0] or False}, context)
        return created_id
