##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    credit_sale_exception = fields.Monetary(compute='_compute_credit_sale_exception',
        string='Total Receivable', help="Total amount this customer owes you (including not invoiced sale orders).",
        groups='account.group_account_invoice,account.group_account_readonly'
    )

    @api.constrains('credit_limit', 'use_partner_credit_limit')
    def check_credit_limit_edition(self):
        # TODO verificar cual es el metodo has_group / has_groups que mas se usa
        if not self.env.user.has_groups(''):
            raise Warnin

    @api.depends_context('company')
    def _compute_credit_sale_exception(self):
        if not self.use_partner_credit_limit:
                self.credit_sale_exception = 0
        else:
            domain = [
                    ('order_id.partner_id.commercial_partner_id', '=', self.commercial_partner_id.id),
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

            domain = [
                    ('move_id.partner_id.commercial_partner_id', '=', self.commercial_partner_id.id),
                    ('move_id.move_type', 'in', ['out_invoice', 'out_refund']),
                    ('move_id.state', '=', 'draft'),
            #         ('exclude_from_invoice_tab', '=', False),  VERIFICAR
                    ('sale_line_ids', '=', False)]
            draft_invoice_lines = self.env['account.move.line'].search(domain)
            draft_invoice_lines_amount = 0.0
            # import pdb; pdb.set_trace()
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



            self.credit_sale_exception = to_invoice_amount + draft_invoice_lines_amount + self.credit

