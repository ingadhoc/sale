##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    require_purchase_order_number = fields.Boolean(
        string='Sale Require Origin',
        related='partner_id.require_purchase_order_number',
        help='If true, required purchase order number in sale order',
    )
    purchase_order_number = fields.Char(
        copy=False
    )

    _sql_constraints = [
        ('purchase_order_number_uniq',
         'unique (purchase_order_number, partner_id)',
         'The Purchase Order Number must be unique!')
    ]

    def action_confirm(self):
        sale_order_missing_po_number = self.filtered(
            lambda
            so: so.require_purchase_order_number and
            not so.purchase_order_number)
        if sale_order_missing_po_number:
            raise UserError(_(
                'You cannot confirm a sales order without a'
                ' Purchase Order Number for this partner'))
        return super().action_confirm()

    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super()._create_invoices(grouped, final, date)
        moves.purchase_order_number = ', '.join([x for x in self.mapped('purchase_order_number') if x ] or [])
        return moves
