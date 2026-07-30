##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        msg = (
            "If you use a sale type in the sale order related with invoice "
            'policy "Block Reserve/Block Delivery", then every sale line must '
            "be invoiced and paid before you can validate picking"
        )
        if any(
            self.sudo().filtered(
                lambda x: (
                    x._is_delivery_chain()
                    and x.sale_id.type_id.invoice_policy in ["prepaid", "prepaid_block_delivery"]
                    and not x._check_sale_paid()
                )
            )
        ):
            raise UserError(_(msg))
        return super().button_validate()

    def action_assign(self):
        msg = (
            "If you use a sale type in the sale order related with invoice"
            ' policy "Prepaid - Block Reserve" , then every sale line must '
            "be invoiced and paid before you can reserve qty to this picking"
        )
        prepaid_unpaid = self.sudo().filtered(
            lambda x: x.picking_type_id.code == "outgoing"
            and x.sale_id.type_id.invoice_policy == "prepaid"
            and not x._check_sale_paid()
        )
        if prepaid_unpaid and self._context.get("prepaid_raise"):
            raise UserError(_(msg))
        elif prepaid_unpaid and not self._context.get("prepaid_raise"):
            self -= prepaid_unpaid
            # do not call super if not self because it raise an error
            if not self:
                return True
        return super(StockPicking, self).action_assign()

    def _check_sale_paid(self):
        precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        invoice_status = (
            self.sale_id.mapped("order_line.invoice_lines.move_id")
            .filtered(lambda x: x.move_type == "out_invoice" and x.state != "cancel")
            .mapped("payment_state")
        )
        paid_status = ["paid", "in_payment", "reversed"]
        if (set(invoice_status) - set(paid_status)) or any(
            not float_is_zero(line.qty_to_invoice, precision_digits=precision) for line in self.sale_id.order_line
        ):
            return False
        return True

    def _is_delivery_chain(self):
        """Whether this picking's moves ultimately reach a customer location.

        Relies on stock.move.location_final_id, which core already computes
        as the end of the whole chain of operations a move belongs to (set
        from the route's rule configuration, not from moves that may not be
        created yet). This tells apart delivery legs (pick/pack/out, whose
        chain ends at a customer location) from receipt legs (e.g. a 2-step
        receipt's put-away, whose chain ends in an internal location even
        when it is tied to a sale line for MTO) and from returns (whose
        chain does not end at a customer location either), without needing
        to compare against specific picking types or walk routing rules by
        hand - both of which previously misclassified pickings a warehouse
        routes differently than the default 3-step delivery.
        """
        self.ensure_one()
        return bool(self.move_ids.filtered(lambda m: (m.location_final_id or m.location_dest_id).usage == "customer"))
