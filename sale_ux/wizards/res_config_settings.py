##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    # agregamos sale para que no se llame igual al de account
    group_sale_reference_on_tree_and_main_form = fields.Boolean(
        'Customer reference in list view and form',
        implied_group='sale_ux.group_reference_on_tree_and_main_form',
        # agregamos portal para portal distributor
        group='base.group_user,base.group_portal',
    )

    update_prices_automatically = fields.Boolean(
        'Update Prices Automatically',
    )

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(update_prices_automatically=get_param(
            'sale_ux.update_prices_automatically',
            'False').lower() == 'true'
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('sale_ux.update_prices_automatically',
                  repr(self.update_prices_automatically))
