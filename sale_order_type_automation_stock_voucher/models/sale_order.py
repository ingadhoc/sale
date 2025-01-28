##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _process_pickings(self, pickings, rec):
        if rec.type_id.book_id:
            pickings.write({'book_id': rec.type_id.book_id.id})
        super()._process_pickings(pickings, rec)

    def run_picking_automation(self):
        res = super().run_picking_automation()
        pickings_book_required = self.picking_ids.filtered("book_required")
        if pickings_book_required:
            actions = [pick.do_print_voucher() for pick in pickings_book_required]
            # it is required to update sale order view
            actions.append({'type': 'ir.actions.client', 'tag': 'soft_reload'})
            return {
                'type': 'ir.actions.act_multi',
                'actions': actions,
            }
        return res
