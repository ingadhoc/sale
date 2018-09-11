##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResCompany(models.Model):

    _inherit = "res.company"

    sale_order_validity_days = fields.Integer(
        help='Set days of validity for Sales Order, if null, no validity date '
        'will be filled',
    )
