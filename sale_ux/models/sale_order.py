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

    pricelist_id = fields.Many2one(
        track_visibility='onchange',
    )
    payment_term_id = fields.Many2one(
        track_visibility='onchange',
    )
    force_invoiced_status = fields.Selection([
        ('no', 'Nothing to Invoice'),
        ('invoiced', 'Fully Invoiced')],
        track_visibility='onchange',
        copy=False,
    )
    commercial_partner_id = fields.Many2one(
        'res.partner',
        string='Commercial Entity',
        related='partner_id.commercial_partner_id',
        store=True,
        compute_sudo=True,
    )

    @api.onchange('pricelist_id')
    def _onchange_pricelist(self):
        update_prices_automatically = safe_eval(
            self.env['ir.config_parameter'].sudo().get_param(
                'sale_ux.update_prices_automatically', 'False'))
        if update_prices_automatically:
            self.update_prices()

    def _amount_by_group(self):
        """
        Hacemos esto para disponer de fecha del pedido y cia para calcular
        impuesto con código python (por ej. para ARBA).
        Aparentemente no se puede cambiar el contexto a cosas que se llaman
        desde un onchange (ver https://github.com/odoo/odoo/issues/7472)
        entonces usamos este artilugio
        TODO este cambio seria mas correcto que este en un repo de loc
        argentina pero para no hacer un modulo con tan pocas cosas lo
        hacemos acá, ademas que el repo de odoo-argentina da error en los tests
        si se instala sale (entonces no podemos agregar dep a sale por ahora)
        """
        for order in self:
            date_order = order.date_order or fields.Date.context_today(order)
            order.env.context.date_invoice = date_order
            order.env.context.invoice_company = order.company_id
            super(SaleOrder, order)._amount_by_group()

    @api.multi
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
        if self.force_invoiced_status and not self.user_has_groups(
                'base.group_system'):
            raise ValidationError(_(
                'Only users with "%s / %s" can Set Invoiced manually') % (
                group.category_id.name, group.name))

    def _get_forbidden_state_confirm(self):
        # This is because some reason the button are present when you
        # validate, this way the sale order only validate if the state are
        # 'draft' or 'sent'
        return super()._get_forbidden_state_confirm() | set({'sale'})

    @api.multi
    def update_prices(self):
        # for compatibility with product_pack module
        self.ensure_one()
        pack_installed = 'pack_parent_line_id' in self.order_line._fields
        for line in self.order_line.with_context(
                update_prices=True, pricelist=self.pricelist_id.id).filtered(lambda l: l.product_id.lst_price):
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
                    line.expand_pack_line(write=True)
            line.product_uom_change()
            line._onchange_discount()
        return True

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        invoice_ids = super().action_invoice_create(
            grouped=grouped, final=final)
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for inv in self.env['account.invoice'].browse(invoice_ids).filtered(
            lambda i: float_is_zero(
                i.amount_total, precision_digits=precision) and all(
                [line.quantity <= 0.0 for line in i.invoice_line_ids])):
            inv.type = 'out_refund'
            for line in inv.invoice_line_ids:
                line.quantity = -line.quantity
            # Use additional field helper function (for account extensions)
            for line in inv.invoice_line_ids:
                line._set_additional_fields(inv)
            # Necessary to force computation of taxes.
            # In account_invoice, they are triggered
            # by onchanges, which are not triggered when doing a create.
            inv.compute_taxes()
        return invoice_ids

    @api.multi
    def preview_sale_order(self):
        """ Open sale Preview in a new Tab """
        res = super().preview_sale_order()
        res.update({'target': 'new'})
        return res
