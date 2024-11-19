##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval
from odoo.tools import float_is_zero
from datetime import datetime, timedelta


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    internal_notes = fields.Html('Internal Notes')
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
    def _onchange_pricelist_id_show_update_prices(self):
        super()._onchange_pricelist_id_show_update_prices()
        update_prices_automatically = safe_eval(
            self.env['ir.config_parameter'].sudo().get_param(
                'sale_ux.update_prices_automatically', 'False'))
        if self.order_line and update_prices_automatically:
            # we need to user the same code as odoo in action_update_prices(),
            # because the "message_post" method isn't available over an onchange trigger.

            # for compatibility with product_pack module
            pack_installed = 'pack_parent_line_id' in self.order_line._fields
            if pack_installed:
                pack_lines = self.order_line.with_context(update_prices=True, pricelist=self.pricelist_id.id).filtered(
                    lambda l: l.product_id.pack_ok and l.product_id.pack_component_price != 'ignored')
                super(SaleOrder, self.with_context(lines_to_not_update_ids=pack_lines.ids))._recompute_prices()
                for line in pack_lines:
                    if line.pack_parent_line_id:
                        continue
                    elif line.pack_child_line_ids:
                        if not isinstance(self.id, int):
                            self._compute_pack_lines_prices(line)
                        else:
                            line.expand_pack_line(write=True)
            else:
                super()._recompute_prices()

    @api.onchange('fiscal_position_id')
    def _onchange_fiscal_position_id(self):
        """
        No utilizamos el método action_update_taxes() directamente porque no funciona
        el message_post sin que se encuentre guardado el registro. 
        """
        self.ensure_one()
        lines_to_recompute = self.order_line.filtered(lambda line: not line.display_type)
        lines_to_recompute._compute_tax_id()
        self.show_update_fpos = False

    def action_cancel(self):
        invoice_lines = self.sudo().env["account.move.line"].search([('sale_line_ids', 'in', self.order_line.ids)])
        moves = invoice_lines.mapped('move_id').filtered(
            lambda x: x.move_type in ('out_invoice', 'out_refund') and x.state not in ['cancel', 'draft']
        )
        if moves:
            raise UserError(_(
                "Unable to cancel this sale order. You must first "
                "cancel related bills and pickings."))
        if any(order.locked for order in self):
            #No encontre otra forma de evitar el raise usererror que impide que ordenes se cancelen si el pedido está bloqueado
            cancel_warning = self._show_cancel_wizard()
            if cancel_warning:
                self.ensure_one()
                template_id = self.env['ir.model.data']._xmlid_to_res_id(
                    'sale.mail_template_sale_cancellation', raise_if_not_found=False
                )
                lang = self.env.context.get('lang')
                template = self.env['mail.template'].browse(template_id)
                if template.lang:
                    lang = template._render_lang(self.ids)[self.id]
                ctx = {
                    'default_template_id': template_id,
                    'default_order_id': self.id,
                    'mark_so_as_canceled': True,
                    'default_email_layout_xmlid': "mail.mail_notification_layout_with_responsible_signature",
                    'model_description': self.with_context(lang=lang).type_name,
                }
                self.action_unlock()
                return {
                    'name': _('Cancel %s', self.type_name),
                    'view_mode': 'form',
                    'res_model': 'sale.order.cancel',
                    'view_id': self.env.ref('sale.sale_order_cancel_view_form').id,
                    'type': 'ir.actions.act_window',
                    'context': ctx,
                    'target': 'new'
                }
            else:
                return self._action_cancel()
        else:
            return super().action_cancel()

    @api.constrains('force_invoiced_status')
    def check_force_invoiced_status(self):
        group = self.sudo().env.ref('base.group_system')
        for rec in self:
            if rec.force_invoiced_status and not self.user_has_groups('base.group_system'):
                raise ValidationError(_(
                    'Only users with "%s / %s" can Set Invoiced manually') % (
                    group.category_id.name, group.name))

    # COMENTAMOS PARA FIX TICKET 68773. ToDo: Evaluar
    # def _get_forbidden_state_confirm(self):
    #     # This is because some reason the button are present when you
    #     # validate, this way the sale order only validate if the state are
    #     # 'draft' or 'sent'
    #     return super()._get_forbidden_state_confirm() | set({'sale'})

    def _get_update_prices_lines(self):
        lines = super()._get_update_prices_lines()
        lines_to_not_update_ids = self._context.get('lines_to_not_update_ids', [])
        return lines.filtered(lambda l: l.id not in lines_to_not_update_ids)

    def action_update_prices(self):
        # avoiding execution for empty records
        if not self:
            return
        # for compatibility with product_pack module
        pack_installed = 'pack_parent_line_id' in self.order_line._fields
        if pack_installed:
            pack_lines = self.order_line.with_context(update_prices=True, pricelist=self.pricelist_id.id).filtered(
                lambda l: l.product_id.pack_ok and l.product_id.pack_component_price != 'ignored')
            super(SaleOrder, self).action_update_prices()
            for line in pack_lines:
                if line.pack_parent_line_id:
                    continue
                elif line.pack_child_line_ids:
                    if not isinstance(self.id, int):
                        self._compute_pack_lines_prices(line)
                    else:
                        line.expand_pack_line(write=True)
        else:
            super().action_update_prices()

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
                sol._onchange_product_id_warning()
                sol.product_uom_qty = quantity
                # sol.product_uom_change()
                # sol._onchange_discount()
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

    def _create_invoices(self, grouped=False, final=False, date=None):
        invoices = super()._create_invoices(grouped=grouped, final=final, date=date)
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        filtered_invoices = invoices.filtered(
            lambda i: float_is_zero(i.amount_total, precision_digits=precision) and all(
                [line.quantity <= 0.0 for line in i.invoice_line_ids])
        )
        filtered_invoices.action_switch_move_type()
        filtered_invoices.mapped('invoice_line_ids').mapped(lambda line: line.write({'quantity': abs(line.quantity)}))
        return invoices

    def action_preview_sale_order(self):
        """ Open sale Preview in a new Tab """
        res = super().action_preview_sale_order()
        res.update({'target': 'new'})
        return res

    def _get_invoiceable_lines(self, final=False):
        """Remove if user allow to remove all notes for invoiceable lines"""
        dont_send_notes_to_invoices = self.env['ir.config_parameter'].sudo().get_param('sale_ux.dont_send_notes_to_invoices', 'False') == 'True'
        res = super()._get_invoiceable_lines(final=final)
        if dont_send_notes_to_invoices:
            res -= res.filtered(lambda x: x.display_type == 'line_note')

        return res

    def _prepare_analytic_account_data(self, prefix=None):
        if self.env['ir.config_parameter'].sudo().get_param(
            'sale_ux.analytic_account_without_company', 'False') == 'True':
            self.ensure_one()
            name = self.name
            if prefix:
                name = prefix + ": " + self.name
            plan = self.env['account.analytic.plan'].sudo().search([
            ], limit=1)
            if not plan:
                plan = self.env['account.analytic.plan'].sudo().create({
                    'name': 'Default',
                })
            return {
                'name': name,
                'code': self.client_order_ref,
                'company_id': False,
                'plan_id': plan.id,
                'partner_id': self.partner_id.id,
            }
        return super(SaleOrder, self)._prepare_analytic_account_data(prefix=prefix)

    def _cron_clean_old_quotations(self, website=None):
        cancel_old_quotations = bool(self.env['ir.config_parameter'].sudo().get_param('sale_ux.cancel_old_quotations', False))
        if cancel_old_quotations or website:
            today = fields.Date.today()
            days_to_keep = int(self.env['ir.config_parameter'].sudo().get_param('sale_ux.days_to_keep_quotations', 30))
            oldest_date = today - timedelta(days=days_to_keep)
            domain = [
                ('state', 'in', ['draft', 'sent']),
                ('date_order', '<', oldest_date),
            ]
            quotations_to_cancel = self.env['sale.order']
            if cancel_old_quotations:
                quotations_to_cancel |= self.env['sale.order'].sudo().search(domain + [('website_id', '=', False)])
            if website:
                quotations_to_cancel |= self.env['sale.order'].sudo().search(domain + [('website_id', '!=', False)])
            for quotation in quotations_to_cancel:
                quotation._action_cancel()
                quotation.message_post(body=_("This quotation has been automatically canceled due to its expiration."))

    @api.constrains('pricelist_id')
    def _check_changes_locked_orders(self):
        for rec in self.filtered(lambda x: x.state == 'done'):
            raise ValidationError(_("You cannot modify already locked orders."))
