##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # dejamos este campo por si alguien lo usaba y ademas lo re usamos abajo
    sale_order_ids = fields.Many2many("sale.order", compute="_compute_sale_orders")
    # en la ui agregamos este que seria mejor a nivel performance
    has_sales = fields.Boolean(string="Has Sales?", compute="_compute_has_sales")
    # no almacenado: solo memoiza el chequeo por factura para no recorrer las lineas una
    # vez por linea en _prepare_product_base_line_for_taxes_computation (ver ahi)
    has_downpayment_deduction = fields.Boolean(compute="_compute_has_downpayment_deduction")

    @api.depends("invoice_line_ids.is_downpayment", "invoice_line_ids.display_type")
    def _compute_has_downpayment_deduction(self):
        for move in self:
            move.has_downpayment_deduction = any(
                line.is_downpayment for line in move.invoice_line_ids if line.display_type == "product"
            )

    @api.depends("move_type", "partner_id", "partner_id.lang", "company_id")
    def _compute_narration(self):
        """Override para respetar el parámetro propagate_note desde sale orders"""
        propagate_note = self.env["ir.config_parameter"].sudo().get_param("sale.propagate_note") == "True"

        # Si propagate_note está activado y la factura viene de una SO, no tocar la narración
        if propagate_note:
            invoices_from_so = self.filtered(lambda m: m.invoice_origin)
            invoices_to_compute = self - invoices_from_so
        else:
            invoices_to_compute = self

        # Aplicar la lógica original solo a facturas que no vienen de SO o cuando propagate_note=False
        if invoices_to_compute:
            super(AccountMove, invoices_to_compute)._compute_narration()

    def _compute_sale_orders(self):
        for rec in self:
            rec.sale_order_ids = rec.invoice_line_ids.mapped("sale_line_ids.order_id")

    def _compute_has_sales(self):
        moves = self.filtered(lambda move: move.is_sale_document())
        (self - moves).has_sales = False
        for rec in moves:
            rec.has_sales = any(line for line in rec.invoice_line_ids.mapped("sale_line_ids"))

    # Evaluar en proximas verciones si Odoo lo resuelve
    # Propuesto upstream en https://github.com/odoo/odoo/pull/278963
    def _prepare_product_base_line_for_taxes_computation(self, product_line):
        base_line = super()._prepare_product_base_line_for_taxes_computation(product_line)
        # El wizard de anticipos redondea a la moneda el price_unit del anticipo
        # (_prepare_down_payment_lines_values), asi que no cancela exacto contra las lineas
        # que dedujo cuando el subtotal crudo de alguna cae en medio centavo. Con
        # round_globally ese residuo se amplifica a un centavo entero que aterriza en la
        # linea base mas grande, y puede dar vuelta la factura final a nota de credito.
        # Apuntamos a los importes ya redondeados (price_subtotal), que son los que se
        # facturaron en el anticipo, para que la agregacion cancele exacto.
        if (
            base_line.get("special_type") != "down_payment"
            and self.is_invoice(include_receipts=True)
            and self.company_id.tax_calculation_rounding_method == "round_globally"
            and self.has_downpayment_deduction
        ):
            base_line["manual_total_excluded_currency"] = product_line.price_subtotal
        return base_line

    # Evaluar en proximas verciones si Odoo lo resuelve
    def action_post(self):
        res = super(AccountMove, self).action_post()
        downpayment_lines = self.line_ids.sale_line_ids.filtered(lambda l: l.is_downpayment and not l.display_type)
        for downpayment_line in downpayment_lines:
            # When change currency in downpayment
            if self.currency_id != downpayment_line.currency_id:
                downpayment_invoice_line = self.invoice_line_ids.filtered(
                    lambda l: l.is_downpayment and l.sale_line_ids.ids == downpayment_line.ids
                )
                downpayment_invoice_line.ensure_one()
                price_unit = downpayment_invoice_line.price_unit
                converted_price_unit = self.currency_id._convert(
                    price_unit, downpayment_line.currency_id, self.company_id, self.invoice_date or fields.Date.today()
                )
                downpayment_line.price_unit = converted_price_unit
        return res
