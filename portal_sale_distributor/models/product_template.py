##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    message_partner_ids = fields.Many2many(
        groups="base.group_user,portal_sale_distributor.group_portal_backend_distributor"
    )
