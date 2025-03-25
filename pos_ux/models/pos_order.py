from odoo import api, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model
    def _process_order(self, order, existing_order):
        return super(PosOrder, self.with_context(from_process_order=True))._process_order(
            order=order, existing_order=existing_order
        )

    def _generate_pos_order_invoice(self):
        if self._context.get("from_process_order"):
            return super(
                PosOrder,
                self.filtered(lambda x: not x.session_id.invoice_contingency).with_context(allow_no_partner=True),
            )._generate_pos_order_invoice()
        else:
            return super(PosOrder, self.with_context(allow_no_partner=True))._generate_pos_order_invoice()
