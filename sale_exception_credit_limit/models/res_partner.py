##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api
from odoo.exceptions import ValidationError



class ResPartner(models.Model):
    _inherit = "res.partner"

    credit_with_confirmed_orders = fields.Monetary(compute='_compute_credit_with_confirmed_orders',
        string='Credit Taken', help="Total amount this customer owes you (including not invoiced confirmed sale orders and draft invoices).",
        groups='account.group_account_invoice,account.group_account_readonly'
    )
    user_credit_config = fields.Boolean(compute='_compute_user_credit_config')

    @api.depends_context('uid')
    def _compute_user_credit_config(self):
        self.user_credit_config = self.env.user.has_group('sale_exception_credit_limit.credit_config')

    @api.constrains('credit_limit', 'use_partner_credit_limit')
    def check_credit_limit_group(self):
        """Si esta constraint trae dolores de cabeza la podemos sacar ya que este "bache" de seguridad esta en muchos
        lugares aún mas criticos. es un problema del ORM donde mucho se protege a nivel vista"""
        if not self.env.user.has_group('sale_exception_credit_limit.credit_config') and any(
            not x.parent_id or x.credit_limit != x.parent_id.credit_limit for x in self
        ):
            raise ValidationError('People without Credit limit Configuration Rights cannot modify credit limit parameters')

    @api.depends_context('company')
    def _compute_credit_with_confirmed_orders(self):
        # Sets 0 when use_partner_credit_limit is not set avoiding unnecessary overloads
        if not self.use_partner_credit_limit:
                self.credit_with_confirmed_orders = 0
        else:
            domain = [
                    ('move_id.partner_id.commercial_partner_id', '=', self.commercial_partner_id.id),
                    ('move_id.move_type', 'in', ['out_invoice', 'out_refund']),
                    ('move_id.state', '=', 'draft'),
                    '|',('sale_line_ids', '=', False),
                    ('sale_line_ids.order_id.invoice_status', '=', 'invoiced')]
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

<<<<<<< HEAD
            self.credit_with_confirmed_orders = draft_invoice_lines_amount + self.credit + self.credit_to_invoice
||||||| parent of c173bc85 (temp)
            total_credit = 0.0
            for company in self.env['res.company'].search([]):
                credit = self.with_company(company).credit
                total_credit += company.currency_id._convert(credit, self.env.company.currency_id, self.env.company, fields.Date.today())

            self.credit_with_confirmed_orders = to_invoice_amount + draft_invoice_lines_amount + total_credit
=======
            total_credit = 0.0
            for company in self.env['res.company'].search([]):
                credit = self.sudo().with_company(company).credit
                total_credit += company.currency_id._convert(credit, self.env.company.currency_id, self.env.company, fields.Date.today())

            self.credit_with_confirmed_orders = to_invoice_amount + draft_invoice_lines_amount + total_credit
>>>>>>> c173bc85 (temp)
