##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    show_in_price_checker = fields.Boolean(
        string="Show in Price Checker",
        default=True,
        help="If unchecked, this product will not appear when scanned in the public price checker.",
    )
