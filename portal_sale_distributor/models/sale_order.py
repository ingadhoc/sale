##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    activity_date_deadline = fields.Date(
        groups="base.group_user,"
        "portal_sale_distributor.group_portal_distributor"
    )

    @api.multi
    def action_confirm_distributor(self):
        self.message_post(
            body=_("Pedido confirmado por %s") % self.env.user.name,
            subtype='mt_comment')
        self = self.sudo()
        return self.action_confirm()

    @api.multi
    def print_quotation_distributor(self):
        """imprimiendo con sudo no funciona, es por un tema del controller
        lo que hicimos por ahora es implementar en aeroo la posibilidad de
        mandar la clave "print_with_sudo" para que aeroo lo imprima con sudo
        TODO deberiamos implementar eso tmb en reportes nativos de odoo
        TODO si esto esta implementado tal vez se puede simplificar el metodo
        portal_order_report y el analogo en facturas
        """
        return self.with_context(print_with_sudo=True).print_quotation()

    @api.onchange('partner_id')
    def onchange_partner_id_warning(self):
        """ desactivamos warning para portal distributor
        """
        if self.env.user.has_group(
                'portal_sale_distributor.group_portal_distributor'):
            return {}
        else:
            return super().onchange_partner_id_warning()
