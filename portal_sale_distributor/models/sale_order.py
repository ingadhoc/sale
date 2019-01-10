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
            _("Pedido confirmado por %s") % self.env.user.name,
            subtype='mt_comment')
        self = self.sudo()
        return self.action_confirm()

    @api.multi
    def print_quotation_distributor(self):
        self = self.sudo()
        return self.print_quotation()
