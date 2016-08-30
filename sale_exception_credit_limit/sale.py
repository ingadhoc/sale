# -*- coding: utf-8 -*-
from openerp import models, api


class sale_order(models.Model):
    _inherit = "sale.order"

    @api.multi
    def check_credit_limit_ok(self):
        self.ensure_one()

        domain = [('order_id.partner_id', '=', self.partner_id.id),
                  ('state', 'in', ['sale', 'done'])]
        order_lines = self.env['sale.order.line'].search(domain)

        to_invoice_amount = 0.0
        for line in order_lines:
            # not_invoiced is different from native qty_to_invoice because
            # the last one only consider to_invoice lines the ones
            # that has been delivered or are ready to invoice regarding
            # the invoicing policy. Not_invoiced consider all
            not_invoiced = line.product_uom_qty - line.qty_invoiced
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(
                price, line.order_id.currency_id,
                not_invoiced,
                product=line.product_id, partner=line.order_id.partner_id)
            to_invoice_amount += taxes['total_included']

        available_credit = self.partner_id.credit_limit - \
            self.partner_id.credit - \
            to_invoice_amount

        if self.amount_total > available_credit:
            return False
        return True
