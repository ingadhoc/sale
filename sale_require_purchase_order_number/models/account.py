##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    require_purchase_order_number = fields.Boolean(
        string='Sale Require Origin',
        related='partner_id.require_purchase_order_number',
        readonly=True,)
    purchase_order_number = fields.Char(
        'Purchase Order Number',
        readonly=True, states={'draft': [('readonly', False)]})

    @api.multi
    def invoice_validate(self):
        for o in self:
            if o.require_purchase_order_number and o.type in [
                    'out_invoice', 'out_refund']:
                if not o.purchase_order_number:
                    raise UserError(_(
                        'You cannot confirm invoice without a'
                        ' Purchase Order Number for this partner'))
        return super(AccountInvoice, self).invoice_validate()
