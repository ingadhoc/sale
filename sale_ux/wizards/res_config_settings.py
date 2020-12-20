##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    group_allow_any_user_as_salesman = fields.Boolean(
        "Allow any user as salesman", implied_group='sale_ux.group_allow_any_user_as_salesman')
    show_product_image_on_report = fields.Boolean(
        string="Show Product Image", default=False, config_parameter='sale_ux.show_product_image_on_report')

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

    move_internal_notes = fields.Boolean(
        'Mover notas internas a transferencias de stock y facturas',
    )
    move_note = fields.Boolean(
        'Mover términos y condiciones a transferencias de stock y facturas',
    )

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(move_internal_notes=get_param(
            'sale.propagate_internal_notes') == 'True')
        res.update(move_note=get_param('sale.propagate_note') == 'True')
        res.update(update_prices_automatically=get_param(
            'sale_ux.update_prices_automatically',
            'False').lower() == 'true'
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('sale.propagate_internal_notes',
                  repr(self.move_internal_notes))
        set_param('sale.propagate_note', repr(self.move_note))
        set_param('sale_ux.update_prices_automatically',
                  repr(self.update_prices_automatically))
