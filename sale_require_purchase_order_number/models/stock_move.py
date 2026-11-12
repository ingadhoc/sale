##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _assign_picking_post_process(self, new=False):
        # here and not in _get_new_picking_values, where l10n_cl_edi_stock runs after us in
        # the MRO; this also covers the delivery of a two or three steps route, that is
        # created when the previous picking is validated
        super()._assign_picking_post_process(new=new)
        if new:
            self.picking_id._set_l10n_cl_purchase_order_reference()
