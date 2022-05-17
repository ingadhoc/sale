##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields
from odoo.tools.float_utils import float_is_zero


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def check_credit_limit_ok(self):
        self.ensure_one()
        self = self.sudo()
        credit_limit = self.partner_id.commercial_partner_id.credit_limit
        if not float_is_zero(credit_limit, precision_digits=self.currency_id.decimal_places):
            domain = [
                ('order_id.id', '!=', self.id),
                ('order_id.partner_id.commercial_partner_id', '=', self.partner_id.commercial_partner_id.id),
                # buscamos las que estan a facturar o las no ya que nos interesa
                # la cantidad total y no solo la facturada. Esta busqueda ayuda
                # a que no busquemos en todo lo que ya fue facturado al dope
                ('invoice_status', 'in', ['to invoice', 'no']),
                ('order_id.state', 'in', ['sale', 'done']),
            ]
            order_lines = self.env['sale.order.line'].search(domain)

            # We sum from all the sale orders that are aproved, the sale order
            # lines that are not yet invoiced
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
                total = taxes['total_included']
                if line.order_id.currency_id != line.company_id.currency_id:
                    total = line.order_id.currency_id._convert(
                        taxes['total_included'], line.company_id.currency_id, line.company_id, fields.Date.today())
                to_invoice_amount += total

            # We sum from all the invoices lines that are in draft and not linked
            # to a sale order
            domain = [
                ('move_id.partner_id.commercial_partner_id', '=', self.partner_id.commercial_partner_id.id),
                ('move_id.move_type', 'in', ['out_invoice', 'out_refund']),
                ('move_id.state', '=', 'draft'),
                ('exclude_from_invoice_tab', '=', False),
                ('sale_line_ids', '=', False)]
            draft_invoice_lines = self.env['account.move.line'].search(domain)
            draft_invoice_lines_amount = 0.0
            for line in draft_invoice_lines:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_ids.compute_all(
                    price, line.move_id.currency_id,
                    line.quantity,
                    product=line.product_id, partner=line.move_id.partner_id)
                total = taxes['total_included']
                if line.move_id.currency_id != line.company_id.currency_id:
                    total = line.move_id.currency_id._convert(
                        taxes['total_included'], line.company_id.currency_id, line.company_id, fields.Date.today())
                draft_invoice_lines_amount += total

            available_credit = self.partner_id.commercial_partner_id.credit_limit - \
                self.partner_id.commercial_partner_id.credit - \
                to_invoice_amount - draft_invoice_lines_amount
            amount_total = self.amount_total
            if self.currency_id != self.company_id.currency_id:
                amount_total = self.currency_id._convert(
                    self.amount_total, self.company_id.currency_id, self.company_id, fields.Date.today())
            if amount_total > available_credit:
                return False
        return True
