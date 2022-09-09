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

    def action_confirm_distributor(self):
        self.sudo().message_post(
            body=_("Pedido confirmado por %s") % self.env.user.name,
            subtype_id=self.env.ref('mail.mt_comment').id)
        self = self.sudo()
        return self.action_confirm()

    @api.onchange('partner_id')
    def _onchange_partner_id_warning(self):
        """ desactivamos warning para portal distributor
        """
        if self.env.user.has_group(
                'portal_sale_distributor.group_portal_distributor'):
            return {}
        else:
            return super()._onchange_partner_id_warning()
