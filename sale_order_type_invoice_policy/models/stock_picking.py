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
        delivery_msg = (
            "If you use a sale type in the sale order related with invoice "
            'policy "Block Reserve/Block Delivery", then every sale line must '
            "be invoiced and paid before you can validate picking"
        )
        mto_receipt_msg = (
            "This receipt is linked to a purchase generated to fulfill a Make "
            "To Order (MTO) sale line. Since that sale order's type uses "
            'invoice policy "Block Reserve/Block Delivery", the sale order '
            "must be fully invoiced and paid before you can validate this "
            "receipt."
        )
        blocked = self.sudo().filtered(
            lambda x: (
                x._is_delivery_chain()
                and x.sale_id.type_id.invoice_policy in ["prepaid", "prepaid_block_delivery"]
                and not x._check_sale_paid()
            )
        )
        if blocked:
            msg = delivery_msg if blocked.filtered(lambda x: x._is_customer_delivery()) else mto_receipt_msg
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
        """Whether this picking's moves eventually reach a customer location.

        Identifies pick/pack/out steps regardless of how many intermediate
        picking types a warehouse defines (e.g. several custom Pick
        operation types per product category), instead of relying on the
        single warehouse.pick_type_id/pack_type_id references, which only
        cover the default 3-step route and miss any extra custom ones.
        Return/receipt pickings are excluded naturally, since their moves
        never end up in a customer location.

        Some routes only create the next leg's stock.move once the current
        one is done (instead of upfront at sale confirmation), so rolling up
        move_dest_ids alone misses the chain for pickings validated before
        that next move exists. Falling back to the warehouse's stock.rule
        graph covers that case: rules are static routing configuration, so
        they are already there even when the moves they will generate are
        not.

        The rule graph is direction-blind though: a return leg can land on
        an internal location (e.g. the warehouse's own Stock) from which
        outgoing rules for future sales are still reachable, which would
        wrongly read as "heading to a customer". Returned moves are excluded
        upfront (via move_orig_ids rollup, so a later leg of a multi-step
        return is also caught) before even considering that fallback.
        """
        self.ensure_one()
        moves = self.move_ids
        orig_moves = moves.browse(moves._rollup_move_origs())
        if orig_moves.filtered("origin_returned_move_id"):
            return False

        dest_moves = moves.browse(moves._rollup_move_dests())
        if (moves | dest_moves).filtered(lambda m: m.location_dest_id.usage == "customer"):
            return True

        Rule = self.env["stock.rule"]
        to_visit = set(moves.location_dest_id.ids)
        seen = set()
        while to_visit:
            location_id = to_visit.pop()
            if location_id in seen:
                continue
            seen.add(location_id)
            if self.env["stock.location"].browse(location_id).usage == "customer":
                return True
            next_rules = Rule.search([("location_src_id", "=", location_id), ("active", "=", True)])
            to_visit.update(set(next_rules.location_dest_id.ids) - seen)
        return False

    def _is_customer_delivery(self):
        """Whether this picking's own moves are actually bound for a customer.

        Used only to choose the error message in button_validate(): a
        receipt tied to an unpaid MTO sale line is still blocked by
        _is_delivery_chain() above, but it never truly ends at a customer,
        so it gets the MTO-specific message instead of the generic delivery
        one. stock.move.location_final_id gives the real end of this move's
        own chain, computed by core from its route/rule configuration.
        """
        self.ensure_one()
        return bool(self.move_ids.filtered(lambda m: (m.location_final_id or m.location_dest_id).usage == "customer"))
