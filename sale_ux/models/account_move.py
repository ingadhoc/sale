##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # dejamos este campo por si alguien lo usaba y ademas lo re usamos abajo
    sale_order_ids = fields.Many2many("sale.order", compute="_compute_sale_orders")
    # en la ui agregamos este que seria mejor a nivel performance
    has_sales = fields.Boolean(string="Has Sales?", compute="_compute_has_sales")

    def _compute_sale_orders(self):
        for rec in self:
            rec.sale_order_ids = rec.invoice_line_ids.mapped("sale_line_ids.order_id")

    def _compute_has_sales(self):
        moves = self.filtered(lambda move: move.is_sale_document())
        (self - moves).has_sales = False
        for rec in moves:
            rec.has_sales = any(line for line in rec.invoice_line_ids.mapped("sale_line_ids"))

    # Evaluar en proximas verciones si Odoo lo resuelve
    def action_post(self):
        res = super(AccountMove, self).action_post()
        downpayment_lines = self.line_ids.sale_line_ids.filtered(lambda l: l.is_downpayment and not l.display_type)
        for downpayment_line in downpayment_lines:
            # When change currency in downpayment
            if self.currency_id != downpayment_line.currency_id:
                downpayment_line.price_unit = self.currency_id._convert(
                    downpayment_line.price_unit,
                    downpayment_line.currency_id,
                    self.company_id,
                    self.invoice_date or fields.Date.today(),
                )
            # When change company in downpayment
            if downpayment_line.company_id != self.company_id:
                taxes = downpayment_line.tax_id
                # Buscamos el correcto tax para la compañia sobre la cual estoy vendiendo, siendo
                # esta distinta a la de la factura de anticipo
                correct_company_tax = self.env["account.tax"].search(
                    [
                        ("company_id", "=", downpayment_line.company_id.id),
                        ("type_tax_use", "in", taxes.mapped("type_tax_use")),
                        ("company_price_include", "in", taxes.mapped("company_price_include")),
                        ("amount", "in", taxes.mapped("amount")),
                        ("amount_type", "in", taxes.mapped("amount_type")),
                    ]
                )
                tax = correct_company_tax or False
                downpayment_line.tax_id = tax
        return res
