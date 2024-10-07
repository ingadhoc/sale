##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def assign_book_id(self):
        for rec in self.filtered(
                lambda x: x.type_id.picking_atomation != 'none' and
                x.procurement_group_id):
            pickings = rec.picking_ids.filtered(
                lambda x: x.state not in ('done', 'cancel'))
            if rec.type_id.book_id:
                pickings.write({'book_id': rec.type_id.book_id.id})
            # because of ensure_one on delivery module
            actions = []
            for pick in pickings:
                # append action records to print the reports of the pickings
                #  involves
                if pick.book_required:
                    actions.append(pick.do_print_voucher())
                pick.button_validate()
            if actions:
                return {
                    'actions': actions,
                    'type': 'ir.actions.act_multi',
                }
            else:
                return True

    def action_confirm(self):
        res = super().action_confirm()
        # we use this because compatibility with sale exception module
        if isinstance(res, bool) and res:
            # because it's needed to return actions if exists
            res = self.assign_book_id()
        return res
