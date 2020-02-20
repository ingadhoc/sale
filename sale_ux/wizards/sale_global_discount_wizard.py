##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class SaleGlobalDiscountWizard(models.TransientModel):
    _name = "sale.order.global_discount.wizard"
    _description = "Sale order Global Discount Wizard"

    amount = fields.Float(
        'Discount',
        required=True,
    )

    def confirm(self):
        self.ensure_one()
        order = self.env['sale.order'].browse(
            self._context.get('active_id', False))
        order.order_line.write({'discount': self.amount})
        return True
