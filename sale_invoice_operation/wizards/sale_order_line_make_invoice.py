# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api


class sale_order_line_make_invoice(models.TransientModel):
    _inherit = "sale.order.line.make.invoice"

    @api.multi
    def make_invoices(self):
        """
        Becasue this function dont use _prepare_invoice and writes
        invoice_ids with sql, we manually call add operations to invoices
        """
        res = super(sale_order_line_make_invoice, self).make_invoices()
        sale_lines = self.env['sale.order.line'].browse(
            self._context.get('active_ids', []))
        sale_lines.mapped('order_id').add_operations_to_invoices()
        return res
