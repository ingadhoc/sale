# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductDocument(models.Model):
    _inherit = 'product.document'

    attached_on_sale = fields.Selection(
        groups='sales_team.group_sale_salesman,portal_sale_distributor.group_portal_backend_distributor')
