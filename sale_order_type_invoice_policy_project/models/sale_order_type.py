##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class SaleOrderType(models.Model):
    _inherit = "sale.order.type"

    services_delivered = fields.Boolean(
        string="Exclude prepaid services",
        help="The 'Deliveries' invoice policy is not applicable to prepaid services. "
        "Recommended for Sales Order lines involving discounts or prepaid services.",
    )
