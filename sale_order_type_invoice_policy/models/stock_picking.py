##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        msg = (
            'If you use a sale type in the sale order related with invoice '
            'policy "Block Reserve/Block Delivery", then every sale line must '
            'be invoiced and paid before you can validate picking')
        if any(
            self.sudo().filtered(
                lambda x: x.sale_id.type_id.invoice_policy in ['prepaid', 'prepaid_block_delivery']
                and not x._check_sale_paid())):
            raise UserError(_(msg))
        return super().button_validate()

    def action_assign(self):
        msg = (
            'If you use a sale type in the sale order related with invoice'
            ' policy "Prepaid - Block Reserve" , then every sale line must '
            'be invoiced and paid before you can reserve qty to this picking')
        prepaid_unpaid = self.sudo().filtered(
            lambda x: x.sale_id.type_id.invoice_policy ==
            'prepaid' and not x._check_sale_paid())
        if prepaid_unpaid and self._context.get('prepaid_raise'):
            raise UserError(_(msg))
        elif prepaid_unpaid and not self._context.get('prepaid_raise'):
            self -= prepaid_unpaid
            # do not call super if not self because it raise an error
            if not self:
                return True
        return super(StockPicking, self).action_assign()

    def _check_sale_paid(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        invoice_status = self.sale_id.mapped(
            'order_line.invoice_lines.move_id.invoice_payment_state')
        if (set(invoice_status) - set(['paid'])) or any(
                not float_is_zero(line.qty_to_invoice, precision_digits=precision)
                for line in self.sale_id.order_line):
            return False
        return True
