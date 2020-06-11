##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class SaleGlobalDiscountWizard(models.TransientModel):

    _inherit = "sale.order.global_discount.wizard"

    discount1 = fields.Boolean(
        string='Discount 1',
    )
    discount2 = fields.Boolean(
        string='Discount 2',
    )
    discount3 = fields.Boolean(
        string='Discount 3',
    )
    discount1_amount = fields.Float()
    discount2_amount = fields.Float()
    discount3_amount = fields.Float()
    amount = fields.Float(
        required=False,
    )

    def confirm(self):
        self.ensure_one()
        order = self.env['sale.order'].browse(
            self._context.get('active_id', False))
        for line in order.order_line:
            if self.discount1:
                line.discount1 = self.discount1_amount
            if self.discount2:
                line.discount2 = self.discount2_amount
            if self.discount3:
                line.discount3 = self.discount3_amount
        return True
