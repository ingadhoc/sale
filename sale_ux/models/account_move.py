##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

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

    # Evaluar en próximas versiones si Odoo lo resuelve
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
