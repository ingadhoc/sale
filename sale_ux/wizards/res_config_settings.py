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
    )
