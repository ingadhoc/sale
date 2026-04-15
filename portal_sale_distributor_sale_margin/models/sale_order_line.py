##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    margin = fields.Float(groups="base.group_user,portal_sale_distributor.group_portal_backend_distributor")
    margin_percent = fields.Float(groups="base.group_user,portal_sale_distributor.group_portal_backend_distributor")
    purchase_price = fields.Float(groups="base.group_user,portal_sale_distributor.group_portal_backend_distributor")
