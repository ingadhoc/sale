##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    require_purchase_order_number = fields.Boolean(
        string='Sale Require Origin',
        related='partner_id.require_purchase_order_number',
    )
    manual_purchase_order_number = fields.Char(
        'PO Number',
        states={'cancel': [('readonly', True)],
                'done': [('readonly', True)]},
    )
    purchase_order_number = fields.Char(
        compute='_compute_purchase_order_number',
        inverse='_inverse_purchase_order_number',
        states={'cancel': [('readonly', True)],
                'done': [('readonly', True)]},
    )

    @api.depends('group_id', 'sale_id')
    def _compute_purchase_order_number(self):
        for rec in self:
            rec.purchase_order_number = rec.manual_purchase_order_number\
                if rec.manual_purchase_order_number\
                else rec.sale_id.purchase_order_number

    def _inverse_purchase_order_number(self):
        for rec in self:
            rec.manual_purchase_order_number = rec.purchase_order_number

    def action_done(self):
        picking_missing_po_number = self.filtered(
            lambda pick: pick.require_purchase_order_number
            and pick.picking_type_code
            == 'outgoing' and not pick.purchase_order_number)
        if picking_missing_po_number:
            raise UserError(_(
                'You cannot transfer products without a Purchase'
                ' Order Number for this partner'))
        return super().action_done()
