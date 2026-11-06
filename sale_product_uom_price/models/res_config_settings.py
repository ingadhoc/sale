##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    report_in_product_uom = fields.Boolean(
        string="Show Product Unit on Quotations",
        config_parameter="sale_product_uom_price.report_in_product_uom",
        help="On the quotation PDF and the online quotation, lines sold in another unit (e.g. a packaging) "
        "show quantity and unit price in the product unit.",
    )
