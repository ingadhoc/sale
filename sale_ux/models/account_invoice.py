##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api


class AccountInvoice(models.Model):

    _inherit = 'account.invoice'

    sale_order_ids = fields.Many2many(
        'sale.order',
        compute='_compute_sale_orders'
    )

    @api.multi
    def _compute_sale_orders(self):
        for rec in self:
            rec.sale_order_ids = rec.invoice_line_ids.mapped(
                'sale_line_ids.order_id')
