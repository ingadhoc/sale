##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    credit_with_confirmed_orders = fields.Monetary(
        compute="_compute_credit_with_confirmed_orders",
        string="Credit Taken",
        help="Total amount this customer owes you (including not invoiced confirmed sale orders and draft invoices).",
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    user_credit_config = fields.Boolean(compute="_compute_user_credit_config")

    @api.depends_context("uid")
    def _compute_user_credit_config(self):
        self.user_credit_config = self.env.user.has_group("sale_exception_credit_limit.credit_config")

    def write(self, vals):
        """Si esta constraint trae dolores de cabeza la podemos sacar ya que este "bache" de seguridad esta en muchos
        lugares aún mas criticos. Es un problema del ORM donde mucho se protege a nivel vista"""
        if "credit_limit" in vals or "use_partner_credit_limit" in vals:
            for record in self:
                if not self.env.user.has_group("sale_exception_credit_limit.credit_config"):
                    new_credit_limit = vals.get("credit_limit", record.credit_limit)
                    if not record.parent_id or new_credit_limit != record.parent_id.credit_limit:
                        raise ValidationError(
                            "People without Credit limit Configuration Rights cannot modify credit limit parameters"
                        )
        return super().write(vals)

    @api.depends_context("company")
    def _compute_credit_with_confirmed_orders(self):
        # Set to 0 if use_partner_credit_limit is not enabled to avoid unnecessary computations
        for rec in self:
            if not rec.use_partner_credit_limit:
                rec.credit_with_confirmed_orders = 0
            else:
                company_id = self.env.company

                domain = [
                    ("order_id.partner_id.commercial_partner_id", "=", rec.commercial_partner_id.id),
                    # We look for order lines that are to be invoiced or not yet invoiced, since we are interested
                    # in the total amount, not just the invoiced part. This search helps avoid including fully invoiced orders.
                    ("invoice_status", "in", ["to invoice", "no"]),
                    ("order_id.state", "in", ["sale", "done"]),
                ]
                order_lines = rec.env["sale.order.line"].sudo().search(domain)

                # Sum the amounts from all approved sale orders for order lines that are not yet invoiced
                to_invoice_amount = 0.0
                for line in order_lines:
                    # not_invoiced differs from the native qty_to_invoice:
                    # qty_to_invoice only considers lines ready to be invoiced according to the invoicing policy,
                    # while not_invoiced considers all lines regardless of delivery or readiness.
                    not_invoiced = line.product_uom_qty - line.qty_invoiced
                    if rec.env["sale.order.line"]._fields.get("quantity_returned"):
                        not_invoiced -= line.quantity_returned
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_id.compute_all(
                        price,
                        line.order_id.currency_id,
                        not_invoiced,
                        product=line.product_id,
                        partner=line.order_id.partner_id,
                    )
                    total = taxes["total_included"]
                    if line.order_id.currency_id != company_id.currency_id:
                        total = line.order_id.currency_id._convert(
                            taxes["total_included"], company_id.currency_id, company_id, fields.Date.today()
                        )
                    to_invoice_amount += total

                domain = [
                    ("move_id.partner_id.commercial_partner_id", "=", rec.commercial_partner_id.id),
                    ("move_id.move_type", "in", ["out_invoice", "out_refund"]),
                    ("move_id.state", "=", "draft"),
                    # Include lines without sale_line_ids or those whose related sale order is fully invoiced
                    "|",
                    ("sale_line_ids", "=", False),
                    ("sale_line_ids.order_id.invoice_status", "=", "invoiced"),
                ]
                draft_invoice_lines = rec.env["account.move.line"].sudo().search(domain)
                draft_invoice_lines_amount = 0.0
                for line in draft_invoice_lines:
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_ids.compute_all(
                        price,
                        line.move_id.currency_id,
                        line.quantity,
                        product=line.product_id,
                        partner=line.move_id.partner_id,
                    )
                    total = taxes["total_included"]
                    if line.move_id.currency_id != company_id.currency_id:
                        total = line.move_id.currency_id._convert(
                            taxes["total_included"], company_id.currency_id, company_id, fields.Date.today()
                        )
                    draft_invoice_lines_amount += total

                # Sum the credit for all companies, converting to the current company currency
                total_credit = 0.0
                for company in rec.env["res.company"].search([]):
                    credit = rec.sudo().with_company(company).credit
                    total_credit += company.currency_id._convert(
                        credit, company_id.currency_id, company_id, fields.Date.today()
                    )

                rec.credit_with_confirmed_orders = to_invoice_amount + draft_invoice_lines_amount + total_credit
