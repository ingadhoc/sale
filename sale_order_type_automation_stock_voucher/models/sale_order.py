##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _process_pickings(self):
        if self.type_id.book_id:
            pickings = self.picking_ids.filtered(lambda x: x.state not in ("done", "cancel"))
            pickings.write({"book_id": self.type_id.book_id.id})
        super()._process_pickings()

    def run_picking_automation(self):
        res = super().run_picking_automation()
        pickings_book_required = self.picking_ids.filtered("book_required")
        if pickings_book_required:
            actions = [pick.do_print_voucher() for pick in pickings_book_required]
            return {
                "type": "ir.actions.client",
                "tag": "do_multi_print",
                "params": {
                    "reports": actions,
                },
            }
        return res
