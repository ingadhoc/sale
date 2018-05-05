##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    require_purchase_order_number = fields.Boolean(
        string='Require Purchase Order Number')
