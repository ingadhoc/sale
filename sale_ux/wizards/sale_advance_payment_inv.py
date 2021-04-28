##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleAdvancePaymentInvWizard(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    amount_total = fields.Float(
        string='Down Payment Amount With Taxes',
        compute='_compute_amount_total',
        inverse='_inverse_amount_total',
        digits='Account',
    )

    @api.onchange('amount_total', 'deposit_taxes_id')
    def _inverse_amount_total(self):
        self.ensure_one()
        sale_obj = self.env['sale.order']
        order = sale_obj.browse(self._context.get('active_ids'))[0]
        tax_percent = 0.0
        for tax in self.deposit_taxes_id.filtered(
                lambda x: not x.price_include):
            if tax.amount_type == 'percent':
                tax_percent += tax.amount
            elif tax.amount_type == 'partner_tax':
                # ugly compatibility with l10n_ar l10n_ar_account_withholding
                tax_percent += tax.get_partner_alicuot(
                    order.partner_id,
                    fields.Date.context_today(self)).alicuota_percepcion
            else:
                raise ValidationError(_(
                    'You can only set amount total if taxes are of type '
                    'percentage'))
        total_percent = (1 + tax_percent / 100) or 1.0
        self.amount = self.amount_total / total_percent

    @api.depends('deposit_taxes_id', 'amount')
    def _compute_amount_total(self):
        """
        For now we implement inverse only for percent taxes. We could extend to
        other by simulating tax.price_include = True, computing tax and
        then restoring tax.price_include = False.
        """
        sale_obj = self.env['sale.order']
        order = sale_obj.browse(self._context.get('active_ids'))[0]

        if self.deposit_taxes_id:
            taxes = self.deposit_taxes_id.compute_all(
                self.amount, order.company_id.currency_id,
                1.0, product=self.product_id,
                partner=order.partner_id)
            self.amount_total = taxes['total_included']
        else:
            self.amount_total = self.amount

    def _create_invoice(self, order, so_line, amount):
        invoice = super()._create_invoice(
            order=order, so_line=so_line, amount=amount)
        propagate_internal_notes = self.env['ir.config_parameter'].sudo(
        ).get_param('sale.propagate_internal_notes') == 'True'
        propagate_note = self.env['ir.config_parameter'].sudo(
        ).get_param('sale.propagate_note') == 'True'
        # we use sudo to prevent error with sales user when create the invoice
        if propagate_internal_notes:
            invoice.sudo().internal_notes = order.internal_notes
        if not propagate_note:
            invoice.sudo().comment = False
        return invoice
