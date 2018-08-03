##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    restrict_sales = fields.Selection(
        [('yes', 'Yes'), ('amount_depends', 'Depends on the amount')],
        'Restrict Sales?',
        help="Restrict Sales to Unapproved Partners?"
    )
    restrict_sales_amount = fields.Float(
        'Restrict Amounts Greater Than'
    )
