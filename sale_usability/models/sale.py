# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, fields, _
from openerp.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def _amount_all(self):
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
        date_order = self.date_order or fields.Date.context_today(self)
        self.env.context.date_invoice = date_order
        self.env.context.invoice_company = self.company_id
        return super(SaleOrder, self)._amount_all()

    manually_set_invoiced = fields.Boolean(
        string='Manually Set Invoiced?',
        help='If you set this field to True, then all lines invoiceable lines'
        'will be set to invoiced?',
        track_visibility='onchange',
    )

    @api.multi
    def action_cancel(self):
        for order in self:
            for inv in order.invoice_ids:
                if inv and inv.state not in ('cancel', 'draft'):
                    raise UserError(_(
                        "Unable to cancel this sale order. You must first "
                        "cancel related bills and pickings."))
        return super(SaleOrder, self).action_cancel()

    @api.multi
    def button_reopen(self):
        self.write({'state': 'sale'})

    @api.multi
    def write(self, vals):
        self.check_manually_set_invoiced(vals)
        return super(SaleOrder, self).write(vals)

    @api.model
    def create(self, vals):
        self.check_manually_set_invoiced(vals)
        return super(SaleOrder, self).create(vals)

    @api.model
    def check_manually_set_invoiced(self, vals):
        if vals.get('manually_set_invoiced') and not self.user_has_groups(
                'base.group_system'):
            group = self.env.ref('base.group_system').sudo()
            raise UserError(_(
                'Only users with "%s / %s" can Set Invoiced manually') % (
                group.category_id.name, group.name))

    # @api.multi
    # def button_set_invoiced(self):
    #     if not self.user_has_groups('base.group_system'):
    #         group = self.env.ref('base.group_system').sudo()
    #         raise UserError(_(
    #             'Only users with "%s / %s" can Set Invoiced manually') % (
    #             group.category_id.name, group.name))
    #     self.order_line.write({'qty_to_invoice': 0.0})
    #     self.message_post(body='Manually setted as invoiced')
