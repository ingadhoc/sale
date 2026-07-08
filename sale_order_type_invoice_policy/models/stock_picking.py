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
<<<<<<< 45158847ecfb019e152733cc2218df6e704a0b9d
                    x.picking_type_id.code == "outgoing"
||||||| f24c9bcd7b4cfaa86e9db2e77a40d71dbb223c0e
                    (
                        x.picking_type_id.code == "outgoing"
                        or x.picking_type_id
                        in (x.picking_type_id.warehouse_id.pick_type_id | x.picking_type_id.warehouse_id.pack_type_id)
                    )
=======
                    x._is_delivery_chain()
>>>>>>> bc8c628efebe157d725705ead2330519dcbdad33
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
        if prepaid_unpaid and self.env.context.get("prepaid_raise"):
            raise UserError(_(msg))
        elif prepaid_unpaid and not self.env.context.get("prepaid_raise"):
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
        """
        self.ensure_one()
        moves = self.move_ids
        dest_moves = moves.browse(moves._rollup_move_dests())
        return bool((moves | dest_moves).filtered(lambda m: m.location_dest_id.usage == "customer"))
