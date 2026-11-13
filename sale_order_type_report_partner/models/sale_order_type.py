##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class SaleOrderType(models.Model):
    _inherit = "sale.order.type"

    report_partner_id = fields.Many2one(
        "res.partner",
        string="Report Partner",
        help="Partner whose name, address, tax id and image are printed on the "
        "sale order report header, instead of the company ones. Useful when "
        "several commercial brands share the same legal entity.",
    )
