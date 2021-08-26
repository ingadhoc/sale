##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval
from odoo.tools import float_is_zero


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    internal_notes = fields.Text('Internal Notes')
    pricelist_id = fields.Many2one(
        tracking=True,
    )
    payment_term_id = fields.Many2one(
        tracking=True,
    )
    force_invoiced_status = fields.Selection([
        ('no', 'Nothing to Invoice'),
        ('invoiced', 'Fully Invoiced')],
        tracking=True,
        copy=False,
    )
    commercial_partner_id = fields.Many2one(
        'res.partner',
        string='Commercial Entity',
        related='partner_id.commercial_partner_id',
        store=True,
        compute_sudo=True,
    )

    def _prepare_invoice(self):
        vals = super(SaleOrder, self)._prepare_invoice()
        propagate_internal_notes = self.env['ir.config_parameter'].sudo(
        ).get_param('sale.propagate_internal_notes') == 'True'
        propagate_note = self.env['ir.config_parameter'].sudo(
        ).get_param('sale.propagate_note') == 'True'
        if propagate_internal_notes and self.internal_notes:
            vals.update({
                'internal_notes': self.internal_notes})
        if 'narration' in vals and not propagate_note:
            vals.pop('narration')
        company = self._context.get('force_company', False) and self.env['res.company'].browse(
            self._context.get('force_company')) or self.env.company
        if not propagate_note and self.env['ir.config_parameter'].sudo().get_param(
                'account.use_invoice_terms') and company.invoice_terms:
            vals['narration'] = company.invoice_terms
        return vals

    @api.onchange('pricelist_id')
    def _onchange_pricelist(self):
        update_prices_automatically = safe_eval(
            self.env['ir.config_parameter'].sudo().get_param(
                'sale_ux.update_prices_automatically', 'False'))
        if update_prices_automatically:
            self.update_prices()

    def action_cancel(self):
        invoices = self.mapped('invoice_ids').filtered(
            lambda x: x.state not in ['cancel', 'draft'])
        if invoices:
            raise UserError(_(
                "Unable to cancel this sale order. You must first "
                "cancel related bills and pickings."))
        return super().action_cancel()

    @api.constrains('force_invoiced_status')
    def check_force_invoiced_status(self):
        group = self.sudo().env.ref('base.group_system')
        for rec in self:
            if rec.force_invoiced_status and not self.user_has_groups('base.group_system'):
                raise ValidationError(_(
                    'Only users with "%s / %s" can Set Invoiced manually') % (
                    group.category_id.name, group.name))

    def _get_forbidden_state_confirm(self):
        # This is because some reason the button are present when you
        # validate, this way the sale order only validate if the state are
        # 'draft' or 'sent'
        return super()._get_forbidden_state_confirm() | set({'sale'})

    def update_prices(self):
        # for compatibility with product_pack module
        self.ensure_one()
        pack_installed = 'pack_parent_line_id' in self.order_line._fields
        for line in self.order_line.with_context(
                update_prices=True, pricelist=self.pricelist_id.id).filtered(
                lambda l: l.product_id.price
                or (pack_installed and l.product_id.pack_ok and l.product_id.pack_component_price != 'ignored')):
            # ponemos descuento en cero por las dudas en dos casos:
            # 1) si estamos cambiando de lista que discrimina descuento
            #  a lista que los incluye
            # 2) o estamos actualizando precios
            # (no sabemos de que lista venimos) a una lista que no discrimina
            #  descuentos y existen listas que discriminan los
            if hasattr(self, '_origin') and self._origin.pricelist_id.\
                discount_policy == 'with_discount' and self.\
                pricelist_id.discount_policy != 'with_discount' or self.\
                    pricelist_id.discount_policy == 'with_discount'\
                    and self.env['product.pricelist'].search(
                        [('discount_policy', '!=', 'with_discount')], limit=1):
                line.discount = False
            if pack_installed:
                if line.pack_parent_line_id:
                    continue
                elif line.pack_child_line_ids:
                    if not isinstance(self.id, int):
                        self._compute_pack_lines_prices(line)
                    else:
                        line.expand_pack_line(write=True)

            line.product_uom_change()
            line._onchange_discount()
        return True

    def _compute_pack_lines_prices(self, line):
        """ This method is for the case when came from an onchange and the original method
        doesn't works with _origin and the values aren't change.
        """
        if line.product_id.pack_ok and line.pack_type == "detailed":
            for subline in line.product_id.get_pack_lines():
                quantity = subline.quantity * line.product_uom_qty
                line_vals = {
                    "order_id": self._origin.id,
                    "product_id": subline.product_id.id or False,
                    "pack_depth": line.pack_depth + 1,
                    "company_id": self.company_id.id,
                    "pack_modifiable": line.product_id.pack_modifiable,
                }
                sol = line.new(line_vals)
                sol.order_id.pricelist_id = self.pricelist_id
                sol.product_id_change()
                sol.product_uom_qty = quantity
                sol.product_uom_change()
                sol._onchange_discount()
                pack_price_types = {"totalized", "ignored"}
                sale_discount = 0.0
                price_unit = sol.price_unit
                if line.product_id.pack_component_price == "detailed":
                    sale_discount = 100.0 - ((100.0 - sol.discount) *
                                             (100.0 - subline.sale_discount) /
                                             100.0)
                elif (
                    line.product_id.pack_type == "detailed"
                    and line.product_id.pack_component_price in pack_price_types
                ):
                    price_unit = 0.0
                line.pack_child_line_ids.filtered(
                    lambda x: x.product_id.id == subline.product_id.id).update(
                    {'price_unit': price_unit, 'discount': sale_discount})

    def _create_invoices(self, grouped=False, final=False):
        invoices = super()._create_invoices(
            grouped=grouped, final=final)
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for inv in invoices.filtered(
            lambda i: float_is_zero(i.amount_total, precision_digits=precision) and all(
                [line.quantity <= 0.0 for line in i.invoice_line_ids])):
            inv.type = 'out_refund'
            for line in inv.invoice_line_ids:
                line.quantity = -line.quantity
        return invoices

    def preview_sale_order(self):
        """ Open sale Preview in a new Tab """
        res = super().preview_sale_order()
        res.update({'target': 'new'})
        return res
