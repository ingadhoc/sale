##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    activity_date_deadline = fields.Date(
        groups="base.group_user,"
        "portal_sale_distributor.group_portal_distributor"
    )
