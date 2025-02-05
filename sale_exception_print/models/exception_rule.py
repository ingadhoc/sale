##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    block_print = fields.Boolean(
        "Block Send Quotation",
    )
